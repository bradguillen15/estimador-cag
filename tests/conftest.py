"""Shared fixtures. The real LLM is never called: tests use fakes at its boundary."""

import os

# app.config reads the environment at import time, so pin deterministic, offline settings first.
# Explicit env vars win over the developer's .env, so a real key can never be picked up.
os.environ.update(
    {
        "OPEN_API_KEY": "test-key",
        "ANTROPIC_API_KEY": "test-key",
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-test",
        "APP_ENV": "development",
        "LOG_LEVEL": "WARNING",
    }
)

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from openai.resources.chat.completions import Completions  # noqa: E402

from app.dependencies import get_estimation_service  # noqa: E402
from app.main import app  # noqa: E402
from app.services.estimation_service import EstimationService  # noqa: E402
from app.services.llm.base import GenerationMetrics  # noqa: E402

VALID_REQUEST: dict[str, str] = {
    "description": "Portal interno para reservar salas con calendario y avisos por email.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "line_items",
}


@pytest.fixture(autouse=True)
def _forbid_real_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Safety net: any code path that reaches the real OpenAI SDK fails the test."""

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("A test tried to call the real OpenAI API")

    monkeypatch.setattr(Completions, "create", _blocked)


class FakeProvider:
    """In-memory ``StreamingLLMProvider``: records prompts and replays a scripted answer."""

    name = "fake"
    model = "fake-model"

    def __init__(
        self,
        text: str = "## Estimación: Demo\n\n**Total estimado: 40 horas**",
        tokens: list[str] | None = None,
        error: Exception | None = None,
        fail_after: int | None = None,
    ) -> None:
        self.text = text
        self.tokens = tokens if tokens is not None else ["## Estimación", ": Demo", "\n\nTotal"]
        self.error = error
        self.fail_after = fail_after
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.text

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]:
        self.calls.append((system_prompt, user_prompt))
        for index, token in enumerate(self.tokens):
            if self.error and self.fail_after == index:
                raise self.error
            yield token
        if self.error and self.fail_after is None:
            raise self.error
        if metrics is not None:
            metrics.model = self.model
            metrics.input_tokens = 100
            metrics.output_tokens = 20
            metrics.latency_seconds = 0.5


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def client(fake_provider: FakeProvider) -> Iterator[TestClient]:
    """API client whose estimation service talks to ``fake_provider``."""
    app.dependency_overrides[get_estimation_service] = lambda: EstimationService(fake_provider)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
