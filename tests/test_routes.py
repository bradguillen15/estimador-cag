"""HTTP/SSE routes with the service injected via ``dependency_overrides`` (fake provider)."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.exceptions import LLMProviderError, PromptTemplateError
from app.services.estimation_service import PROMPT_VERSION
from tests.conftest import VALID_REQUEST, FakeProvider


def _sse_events(body: str) -> list[tuple[str, Any]]:
    """Parses an SSE body into ``(event, json_payload)`` pairs, skipping keep-alive comments."""
    events: list[tuple[str, Any]] = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        name, data = "message", []
        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            field, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if field == "event":
                name = value
            elif field == "data":
                data.append(value)
        if data:
            events.append((name, json.loads("\n".join(data))))
    return events


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_context_returns_the_injected_examples(client: TestClient) -> None:
    body = client.get("/api/v1/context").json()
    assert body["prompt_version"] == PROMPT_VERSION
    assert "### Example 1" in body["examples_markdown"]


# --- POST /estimate ---------------------------------------------------------------------------


def test_estimate_returns_the_model_text_and_prompt_version(client: TestClient, fake_provider: FakeProvider) -> None:
    response = client.post("/api/v1/estimate", json=VALID_REQUEST)

    assert response.status_code == 200
    assert response.json() == {"text": fake_provider.text, "prompt_version": PROMPT_VERSION}
    _, user_prompt = fake_provider.calls[0]
    assert VALID_REQUEST["description"] in user_prompt


@pytest.mark.parametrize(
    "payload",
    [
        {**VALID_REQUEST, "description": "corto"},
        {**VALID_REQUEST, "output_format": "pdf"},
        {key: value for key, value in VALID_REQUEST.items() if key != "project_type"},
    ],
)
def test_estimate_rejects_invalid_input_without_calling_the_llm(
    client: TestClient, fake_provider: FakeProvider, payload: dict[str, str]
) -> None:
    response = client.post("/api/v1/estimate", json=payload)

    assert response.status_code == 422
    assert fake_provider.calls == []


@pytest.mark.parametrize(
    ("language", "instruction"),
    [("en", "Respond entirely in English"), ("es", "Respond entirely in Spanish"), ("fr", "Respond entirely in Spanish")],
)
def test_estimate_asks_the_model_to_answer_in_the_requested_language(
    client: TestClient, fake_provider: FakeProvider, language: str, instruction: str
) -> None:
    response = client.post("/api/v1/estimate", json={**VALID_REQUEST, "language": language})

    assert response.status_code == 200
    system_prompt, _ = fake_provider.calls[0]
    assert instruction in system_prompt


def test_stream_honours_the_requested_language(client: TestClient, fake_provider: FakeProvider) -> None:
    client.post("/api/v1/estimate/stream", json={**VALID_REQUEST, "language": "en"})
    system_prompt, _ = fake_provider.calls[0]
    assert "Respond entirely in English" in system_prompt


def test_provider_failure_maps_to_502_with_a_safe_message(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.error = LLMProviderError("El proveedor LLM alcanzó su límite de solicitudes.")

    response = client.post("/api/v1/estimate", json=VALID_REQUEST)

    assert response.status_code == 502
    assert response.json() == {"detail": "El proveedor LLM alcanzó su límite de solicitudes."}


def test_prompt_misconfiguration_maps_to_500(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.error = PromptTemplateError("Missing template 'user.j2'")
    response = client.post("/api/v1/estimate", json=VALID_REQUEST)
    assert response.status_code == 500
    assert "user.j2" in response.json()["detail"]


def test_unexpected_errors_do_not_leak_details(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.error = RuntimeError("sk-live-SECRET stack detail")

    response = client.post("/api/v1/estimate", json=VALID_REQUEST)

    assert response.status_code == 500
    assert "SECRET" not in response.text


# --- POST /estimate/stream --------------------------------------------------------------------


def test_stream_emits_tokens_then_a_done_event_with_metadata(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.tokens = ["## Estimación", ": App", "\n\n  - línea con espacios"]

    response = client.post("/api/v1/estimate/stream", json=VALID_REQUEST)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)
    assert [payload for name, payload in events if name == "token"] == fake_provider.tokens
    assert events[-1] == (
        "done",
        {
            "model": "fake-model",
            "provider": "fake",
            "input_tokens": 100,
            "output_tokens": 20,
            "latency_seconds": 0.5,
            "prompt_version": PROMPT_VERSION,
        },
    )


def test_stream_reports_provider_failures_as_an_error_event(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.error = LLMProviderError("El proveedor LLM tardó demasiado en responder.")
    fake_provider.fail_after = 1

    events = _sse_events(client.post("/api/v1/estimate/stream", json=VALID_REQUEST).text)

    assert events[0] == ("token", fake_provider.tokens[0])
    assert events[-1] == ("error", {"detail": "El proveedor LLM tardó demasiado en responder."})
    assert "done" not in [name for name, _ in events]


def test_stream_hides_unexpected_error_details(client: TestClient, fake_provider: FakeProvider) -> None:
    fake_provider.error = RuntimeError("sk-live-SECRET")
    fake_provider.fail_after = 0

    events = _sse_events(client.post("/api/v1/estimate/stream", json=VALID_REQUEST).text)

    assert events == [("error", {"detail": "Error inesperado al generar la estimación."})]


def test_stream_validates_input_before_opening_the_stream(client: TestClient, fake_provider: FakeProvider) -> None:
    response = client.post("/api/v1/estimate/stream", json={**VALID_REQUEST, "detail_level": "extreme"})
    assert response.status_code == 422
    assert fake_provider.calls == []
