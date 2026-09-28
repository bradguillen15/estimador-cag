"""Servicio de llamada al LLM (lógica de negocio)."""

from collections.abc import Iterator
from dataclasses import dataclass
from time import perf_counter

import structlog
from openai import OpenAI

from app.config import settings
from app.logging_config import estimate_cost_usd
from app.prompts.loader import render_estimation_prompt
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


class LLMService:
    def __init__(self) -> None:
        self.provider = "openai"
        self.model = settings.llm_model
        self._client = OpenAI(api_key=settings.open_api_key)

    def generate_from_request(self, request: EstimationRequest) -> str:
        system, user = render_estimation_prompt(request, version=PROMPT_VERSION)
        return self._complete(system, user, stream=False)

    def generate_stream_from_request(
        self,
        request: EstimationRequest,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        system, user = render_estimation_prompt(request, version=PROMPT_VERSION)
        yield from self._complete_stream(system, user, metrics=metrics)

    def _complete(self, system: str, user: str, *, stream: bool = False) -> str:
        del stream  # reserved for symmetry with _complete_stream
        call_logger = logger.bind(model=self.model, provider=self.provider, stream=False)
        call_logger.info("llm_call_started")
        started_at = perf_counter()

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
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

    def _complete_stream(
        self,
        system: str,
        user: str,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        call_logger = logger.bind(model=self.model, provider=self.provider, stream=True)
        call_logger.info("llm_call_started")
        started_at = perf_counter()
        tokens_in: int | None = None
        tokens_out: int | None = None
        finish_reason: str | None = None

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
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
