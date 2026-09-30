"""Estimation use case.

Pipeline (input guardrails run earlier, in ``prepare``): exact cache -> LLM -> output check ->
store. Only answers that completed and passed the output check are cached.
"""

from collections.abc import Iterator, Sequence
from time import perf_counter

import structlog

from app.prompts.loader import PROMPT_VERSION, render_estimation_examples, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from app.services.cache.base import CachedAnswer, NoOpCache, ResponseCache, make_cache_key
from app.services.guardrails.input import InputGuardrails
from app.services.guardrails.output import check_estimation_output
from app.services.llm.base import GenerationMetrics, StreamingLLMProvider

__all__ = ["PROMPT_VERSION", "EstimationService"]

logger = structlog.get_logger()


class EstimationService:
    def __init__(
        self,
        provider: StreamingLLMProvider,
        guardrails: InputGuardrails | None = None,
        cache: ResponseCache | None = None,
        cache_models: Sequence[str] | None = None,
    ) -> None:
        self._provider = provider
        self._guardrails = guardrails or InputGuardrails()
        self._cache = cache if cache is not None else NoOpCache()
        # Part of the cache key: changing the configured model list must not serve old answers.
        self._cache_models = tuple(cache_models) if cache_models else (provider.model,)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    def context_examples(self) -> str:
        """CAG examples the model receives in the system prompt (Markdown)."""
        return render_estimation_examples()

    def prepare(self, request: EstimationRequest) -> EstimationRequest:
        """Runs the input guardrails; returns the request with the sanitized description.

        Raises ``InputRejectedError``. Call it before ``generate``/``generate_stream``, which expect
        an already prepared request.
        """
        safe_description = self._guardrails.check(request.description)
        return request.model_copy(update={"description": safe_description})

    def generate(self, request: EstimationRequest) -> str:
        key = make_cache_key(request, PROMPT_VERSION, self._cache_models)
        cached = self._cache.get(key)
        if cached is not None:
            return cached.text

        system, user = render_estimation_prompt(request)
        text = self._provider.complete(system, user)
        if self._passes_output_check(request, text):
            self._cache.set(key, CachedAnswer(text=text))
        return text

    def generate_stream(
        self,
        request: EstimationRequest,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        started_at = perf_counter()
        key = make_cache_key(request, PROMPT_VERSION, self._cache_models)
        cached = self._cache.get(key)
        if cached is not None:
            if metrics is not None:
                metrics.cache_hit = True
                metrics.model = cached.model or "cache"
                metrics.latency_seconds = round(perf_counter() - started_at, 4)
            # Replay line by line so the client sees the same token events as a live generation.
            yield from cached.text.splitlines(keepends=True)
            return

        system, user = render_estimation_prompt(request)
        chunks: list[str] = []
        for chunk in self._provider.stream(system, user, metrics=metrics):
            chunks.append(chunk)
            yield chunk
        # Reached only when the stream completed (an error or a client disconnect skips it), so a
        # broken stream is never checked nor cached.
        text = "".join(chunks)
        if self._passes_output_check(request, text):
            self._cache.set(key, CachedAnswer(text=text, model=metrics.model if metrics else None))

    @staticmethod
    def _passes_output_check(request: EstimationRequest, text: str) -> bool:
        """Logs a structured warning when the answer breaks the format; such answers are not cacheable."""
        check = check_estimation_output(text, request.language)
        if not check.passed:
            logger.warning(
                "output_check_failed",
                reason=check.reason,
                language=request.language.value,
                prompt_version=PROMPT_VERSION,
                output_chars=len(text),
            )
        return check.passed
