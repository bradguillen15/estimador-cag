"""Servicio de llamada al LLM (lógica de negocio)."""

from collections.abc import Iterator
from dataclasses import dataclass
from textwrap import dedent
from time import perf_counter

import structlog
from openai import OpenAI

from app.config import settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.logging_config import estimate_cost_usd
from app.schemas.estimations import EstimationRequest

logger = structlog.get_logger()

PROMPT_VERSION = "v1"


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
            raise ValueError(
                "La conversación debe terminar con un mensaje de usuario no vacío."
            )

        return [
            {"role": "system", "content": self.system_prompt},
            *turns,
        ]

    def generate_from_request(self, request: EstimationRequest) -> str:
        """Builds a plain user message from the form contract and calls the LLM."""
        user_content = (
            f"Tipo de proyecto: {request.project_type.value}\n"
            f"Nivel de detalle: {request.detail_level.value}\n"
            f"Formato de salida: {request.output_format.value}\n\n"
            f"Descripción del proyecto:\n{request.description.strip()}"
        )
        return self.generate(user_content)

    def generate(self, meeting_transcript: str) -> str:
        call_logger = logger.bind(model=self.model, provider=self.provider, stream=False)
        call_logger.info("llm_call_started")
        started_at = perf_counter()

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=self._messages(
                    [{"role": "user", "content": meeting_transcript}]
                ),
            )
            content = completion.choices[0].message.content
            if not content:
                raise RuntimeError("OpenAI devolvió una respuesta vacía.")

            usage = completion.usage
            tokens_in = usage.prompt_tokens if usage else None
            tokens_out = usage.completion_tokens if usage else None
            latency_ms = round((perf_counter() - started_at) * 1000, 1)
            call_logger.info(
                "llm_call_completed",
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=estimate_cost_usd(self.model, tokens_in, tokens_out),
                finish_reason=completion.choices[0].finish_reason,
                cache_hit=False,
                fallback_used=False,
            )
            return content
        except Exception as exc:
            call_logger.error(
                "llm_call_failed",
                error_type=type(exc).__name__,
                error_msg=str(exc),
                latency_ms=round((perf_counter() - started_at) * 1000, 1),
            )
            raise

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
        call_logger = logger.bind(model=self.model, provider=self.provider, stream=True)
        call_logger.info("llm_call_started")
        started_at = perf_counter()
        tokens_in: int | None = None
        tokens_out: int | None = None
        finish_reason: str | None = None

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=self._messages(conversation),
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if chunk.usage is not None:
                    tokens_in = chunk.usage.prompt_tokens
                    tokens_out = chunk.usage.completion_tokens
                    if metrics is not None:
                        metrics.input_tokens = tokens_in
                        metrics.output_tokens = tokens_out

                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                delta = choice.delta.content
                if delta:
                    yield delta

            latency_ms = round((perf_counter() - started_at) * 1000, 1)
            if metrics is not None:
                metrics.model = self.model
                metrics.latency_seconds = latency_ms / 1000

            call_logger.info(
                "llm_call_completed",
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=estimate_cost_usd(self.model, tokens_in, tokens_out),
                finish_reason=finish_reason,
                cache_hit=False,
                fallback_used=False,
            )
        except Exception as exc:
            call_logger.error(
                "llm_call_failed",
                error_type=type(exc).__name__,
                error_msg=str(exc),
                latency_ms=round((perf_counter() - started_at) * 1000, 1),
            )
            raise
