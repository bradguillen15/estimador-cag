"""Servicio de llamada al LLM (lógica de negocio)."""

from collections.abc import Iterator
from dataclasses import dataclass
from textwrap import dedent
from time import perf_counter

from openai import OpenAI

from app.config import settings
from app.context.examples import ESTIMATION_EXAMPLES


@dataclass
class GenerationMetrics:
    """Métricas de la última llamada al LLM (rellenadas al terminar el stream)."""

    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_seconds: float | None = None

_ROLE_AND_RULES = """\
Eres un Tech Lead con más de 10 años estimando proyectos de software en una consultora.
Recibes la transcripción (o el resumen) de una reunión con un cliente y produces una
estimación de esfuerzo realista, defendible ante el cliente y accionable por el equipo.

## Cómo trabajar
1. Extrae de la transcripción los requisitos funcionales y no funcionales, integraciones,
   plataformas y restricciones de plazo o presupuesto.
2. Marca como supuesto todo lo que necesites para estimar y el cliente no haya dicho
   explícitamente. No inventes requisitos nuevos.
3. Descompón el trabajo en tareas de alto nivel y asigna horas a cada una.
4. Deriva el equipo recomendado y la duración en semanas a partir del total de horas.

## Reglas de estimación
- Los ejemplos son referencia de granularidad, formato y orden de magnitud, no una
  plantilla de cifras: nunca copies las horas de un ejemplo si el alcance difiere.
- Incluye siempre una tarea de testing y QA, y una de diseño UI/UX cuando haya interfaz.
- Expresa las horas como enteros, en múltiplos de 4 cuando sea posible.
- El total debe ser exactamente la suma del desglose. Verifícalo antes de responder.
- Calcula la duración asumiendo ~30 horas productivas por persona y semana, y exprésala
  como un rango (por ejemplo, 6-8 semanas).
- Solo incluye importes en dinero si la transcripción menciona una tarifa horaria o un
  presupuesto; en ese caso calcúlalos a partir del total de horas. Nunca inventes tarifas.
- Si la transcripción es demasiado vaga para estimar, dilo y pide la información concreta
  que falta en lugar de inventar un alcance.
- Responde en español y solo con la estimación en Markdown, sin saludos ni comentarios
  finales."""

_OUTPUT_FORMAT = """\
## Formato de salida obligatorio

Sigue esta estructura. Los ejemplos anteriores no incluyen las secciones "Supuestos" y
"Riesgos y fuera de alcance", pero tu respuesta sí debe incluirlas:

## Estimación: <nombre del proyecto>

### Supuestos
- <supuesto>

### Desglose de tareas
1. <Tarea>: <N> horas

**Total estimado: <N> horas**
**Equipo recomendado: <perfiles>**
**Duración estimada: <N>-<M> semanas**

### Riesgos y fuera de alcance
- <riesgo o exclusión>"""


def _build_system_prompt() -> str:
    examples_block = "\n\n".join(
        (
            f"### Ejemplo {index}\n"
            f"**Resumen de la reunión:**\n{dedent(example['meeting_summary']).strip()}\n\n"
            f"**Estimación generada:**\n{dedent(example['estimation']).strip()}"
        )
        for index, example in enumerate(ESTIMATION_EXAMPLES, start=1)
    )

    return (
        f"{_ROLE_AND_RULES}\n\n"
        "## Ejemplos de estimaciones previas\n\n"
        f"{examples_block}\n\n"
        f"{_OUTPUT_FORMAT}"
    )


class LLMService:
    def __init__(self) -> None:
        self.provider = "openai"
        self.model = settings.llm_model
        self.system_prompt = _build_system_prompt()
        self._client = OpenAI(api_key=settings.open_api_key)

    def _messages(self, conversation: list[dict[str, str]]) -> list[dict[str, str]]:
        """Prepends the CAG system prompt to the conversation turns."""
        turns: list[dict[str, str]] = []
        for message in conversation:
            role = message.get("role", "")
            content = (message.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            turns.append({"role": role, "content": content})

        if not turns or turns[-1]["role"] != "user":
            raise ValueError("La conversación debe terminar con un mensaje de usuario no vacío.")

        return [
            {"role": "system", "content": self.system_prompt},
            *turns,
        ]

    def generate(self, meeting_transcript: str) -> str:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._messages([{"role": "user", "content": meeting_transcript}]),
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI devolvió una respuesta vacía.")
        return content

    def generate_stream(
        self,
        conversation: list[dict[str, str]],
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        """Yields text deltas from the LLM as they arrive.

        ``conversation`` is the full chat history (user/assistant turns). The CAG
        system prompt is prepended automatically.

        If ``metrics`` is provided, it is filled with model, token usage and
        latency when the stream completes.
        """
        started_at = perf_counter()
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=self._messages(conversation),
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if metrics is not None and chunk.usage is not None:
                metrics.input_tokens = chunk.usage.prompt_tokens
                metrics.output_tokens = chunk.usage.completion_tokens

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        if metrics is not None:
            metrics.model = self.model
            metrics.latency_seconds = perf_counter() - started_at

