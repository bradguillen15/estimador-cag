"""EstimationService: renders the prompts and delegates to a (fake) provider."""

import pytest

from app.exceptions import LLMProviderError
from app.prompts.loader import render_estimation_examples, render_estimation_prompt
from app.schemas.estimations import EstimationRequest
from app.services.estimation_service import PROMPT_VERSION, EstimationService
from app.services.llm.base import GenerationMetrics
from tests.conftest import VALID_REQUEST, FakeProvider

REQUEST = EstimationRequest.model_validate(VALID_REQUEST)


def test_generate_sends_the_rendered_prompts_to_the_provider() -> None:
    provider = FakeProvider(text="## Estimación: Salas")
    service = EstimationService(provider)

    assert service.generate(REQUEST) == "## Estimación: Salas"
    assert provider.calls == [render_estimation_prompt(REQUEST, version=PROMPT_VERSION)]


def test_generate_propagates_provider_errors() -> None:
    service = EstimationService(FakeProvider(error=LLMProviderError("caído")))
    with pytest.raises(LLMProviderError, match="caído"):
        service.generate(REQUEST)


def test_generate_stream_yields_tokens_and_forwards_metrics() -> None:
    provider = FakeProvider(tokens=["a", "b", "c"])
    service = EstimationService(provider)
    metrics = GenerationMetrics(model=service.model)

    assert list(service.generate_stream(REQUEST, metrics=metrics)) == ["a", "b", "c"]
    assert provider.calls == [render_estimation_prompt(REQUEST, version=PROMPT_VERSION)]
    assert (metrics.input_tokens, metrics.output_tokens) == (100, 20)


def test_exposes_provider_identity_and_cag_examples() -> None:
    service = EstimationService(FakeProvider())
    assert (service.provider_name, service.model) == ("fake", "fake-model")
    assert service.context_examples() == render_estimation_examples(PROMPT_VERSION)

