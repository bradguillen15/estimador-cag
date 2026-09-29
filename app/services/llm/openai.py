"""OpenAI provider: the only module that knows about the OpenAI SDK."""

from collections.abc import Iterator
from time import perf_counter

import openai
import structlog
from openai import OpenAI

from app.exceptions import LLMProviderError
from app.logging_config import estimate_cost_usd
from app.services.llm.base import GenerationMetrics

logger = structlog.get_logger()


def _to_provider_error(exc: Exception) -> LLMProviderError:
    """Translates SDK failures into a client-safe domain error (raw details stay in the logs)."""
    if isinstance(exc, LLMProviderError):
        return exc
    if isinstance(exc, openai.RateLimitError):
        return LLMProviderError(
            "El proveedor LLM alcanzó su límite de solicitudes. Inténtalo de nuevo en unos segundos."
        )
    if isinstance(exc, openai.APITimeoutError):
        return LLMProviderError("El proveedor LLM tardó demasiado en responder.")
    if isinstance(exc, openai.APIConnectionError):
        return LLMProviderError("No se pudo conectar con el proveedor LLM.")
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return LLMProviderError("El proveedor LLM rechazó las credenciales configuradas.")
    return LLMProviderError("El proveedor LLM devolvió un error al generar la estimación.")


def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, client: OpenAI | None = None) -> None:
        self.model = model
        self._client = client or OpenAI(api_key=api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        call_logger = logger.bind(model=self.model, provider=self.name, stream=False)
        call_logger.info("llm_call_started")
        started_at = perf_counter()

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=_messages(system_prompt, user_prompt),
            )
            content = completion.choices[0].message.content
            if not content:
                raise LLMProviderError("El proveedor LLM devolvió una respuesta vacía.")

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
            raise _to_provider_error(exc) from exc

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        call_logger = logger.bind(model=self.model, provider=self.name, stream=True)
        call_logger.info("llm_call_started")
        started_at = perf_counter()
        tokens_in: int | None = None
        tokens_out: int | None = None
        finish_reason: str | None = None

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=_messages(system_prompt, user_prompt),
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
            raise _to_provider_error(exc) from exc
