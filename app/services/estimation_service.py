"""Estimation use case: renders the prompts and delegates the call to the LLM provider."""

from collections.abc import Iterator

import structlog

from app.prompts.loader import PROMPT_VERSION, render_estimation_examples, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from app.services.guardrails.input import InputGuardrails
from app.services.guardrails.output import check_estimation_output
from app.services.llm.base import GenerationMetrics, StreamingLLMProvider

__all__ = ["PROMPT_VERSION", "EstimationService"]

logger = structlog.get_logger()


class EstimationService:
    def __init__(self, provider: StreamingLLMProvider, guardrails: InputGuardrails | None = None) -> None:
        self._provider = provider
        self._guardrails = guardrails or InputGuardrails()

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
        system, user = render_estimation_prompt(request)
        text = self._provider.complete(system, user)
        self._passes_output_check(request, text)
        return text

    def generate_stream(
        self,
        request: EstimationRequest,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        system, user = render_estimation_prompt(request)
        chunks: list[str] = []
        for chunk in self._provider.stream(system, user, metrics=metrics):
            chunks.append(chunk)
            yield chunk
        # Reached only when the stream completed (an error or a client disconnect skips it).
        self._passes_output_check(request, "".join(chunks))

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
