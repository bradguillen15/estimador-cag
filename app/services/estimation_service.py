"""Caso de uso de estimación: arma los prompts y delega la llamada al proveedor LLM."""

from collections.abc import Iterator

from app.prompts.loader import render_estimation_examples, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from app.services.llm.base import GenerationMetrics, StreamingLLMProvider

PROMPT_VERSION = "v2"


class EstimationService:
    def __init__(self, provider: StreamingLLMProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    def context_examples(self) -> str:
        """Ejemplos CAG que recibe el modelo en el system prompt (Markdown)."""
        return render_estimation_examples(PROMPT_VERSION)

    def generate(self, request: EstimationRequest) -> str:
        system, user = render_estimation_prompt(request, version=PROMPT_VERSION)
        return self._provider.complete(system, user)

    def generate_stream(
        self,
        request: EstimationRequest,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        system, user = render_estimation_prompt(request, version=PROMPT_VERSION)
        yield from self._provider.stream(system, user, metrics=metrics)
