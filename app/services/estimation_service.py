"""Estimation use case: renders the prompts and delegates the call to the LLM provider."""

from collections.abc import Iterator

from app.prompts.loader import PROMPT_VERSION, render_estimation_examples, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from app.services.guardrails.input import InputGuardrails
from app.services.llm.base import GenerationMetrics, StreamingLLMProvider

__all__ = ["PROMPT_VERSION", "EstimationService"]


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
        return self._provider.complete(system, user)

    def generate_stream(
        self,
        request: EstimationRequest,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        system, user = render_estimation_prompt(request)
        yield from self._provider.stream(system, user, metrics=metrics)
