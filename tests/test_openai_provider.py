"""OpenAIProvider: el SDK se sustituye por un cliente falso en su frontera (``chat.completions.create``)."""

from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.exceptions import LLMProviderError
from app.services.llm.base import GenerationMetrics
from app.services.llm.openai import OpenAIProvider

_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
_SECRET = "org-SECRET123 raw provider detail"


class FakeOpenAIClient:
    """Duck-typed stand-in for ``openai.OpenAI``: only ``chat.completions.create`` exists."""

    def __init__(self, create: Callable[..., Any]) -> None:
        self.calls: list[dict[str, Any]] = []

        def _create(**kwargs: Any) -> Any:
            self.calls.append(kwargs)
            return create(**kwargs)

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


def _provider(create: Callable[..., Any]) -> tuple[OpenAIProvider, FakeOpenAIClient]:
    client = FakeOpenAIClient(create)
    return OpenAIProvider(api_key="unused", model="gpt-test", client=client), client  # type: ignore[arg-type]


def _completion(content: str | None, *, usage: bool = True, choices: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")] if choices else [],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30) if usage else None,
    )


def _chunk(content: str | None = None, *, finish: str | None = None, usage: tuple[int, int] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[] if content is None and finish is None else [SimpleNamespace(delta=SimpleNamespace(content=content), finish_reason=finish)],
        usage=SimpleNamespace(prompt_tokens=usage[0], completion_tokens=usage[1]) if usage else None,
    )


def _raiser(exc: Exception) -> Callable[..., Any]:
    def _create(**_: Any) -> Any:
        raise exc

    return _create


SDK_ERRORS: list[tuple[Exception, str]] = [
    (openai.RateLimitError(_SECRET, response=httpx.Response(429, request=_REQUEST), body=None), "límite de solicitudes"),
    (openai.APITimeoutError(request=_REQUEST), "tardó demasiado"),
    (openai.APIConnectionError(message=_SECRET, request=_REQUEST), "No se pudo conectar"),
    (openai.AuthenticationError(_SECRET, response=httpx.Response(401, request=_REQUEST), body=None), "credenciales"),
    (openai.InternalServerError(_SECRET, response=httpx.Response(500, request=_REQUEST), body=None), "devolvió un error"),
]


# --- complete() -------------------------------------------------------------------------------


def test_complete_sends_system_and_user_messages_and_returns_the_text() -> None:
    provider, client = _provider(lambda **_: _completion("## Estimación: Demo"))

    assert provider.complete("SYSTEM", "USER") == "## Estimación: Demo"
    assert client.calls == [
        {
            "model": "gpt-test",
            "messages": [
                {"role": "system", "content": "SYSTEM"},
                {"role": "user", "content": "USER"},
            ],
        }
    ]


@pytest.mark.parametrize("content", ["", None])
def test_complete_rejects_an_empty_answer(content: str | None) -> None:
    provider, _ = _provider(lambda **_: _completion(content))
    with pytest.raises(LLMProviderError, match="vacía"):
        provider.complete("S", "U")


def test_complete_tolerates_missing_usage() -> None:
    provider, _ = _provider(lambda **_: _completion("texto", usage=False))
    assert provider.complete("S", "U") == "texto"


def test_complete_turns_a_malformed_response_into_a_domain_error() -> None:
    provider, _ = _provider(lambda **_: _completion("x", choices=False))
    with pytest.raises(LLMProviderError):
        provider.complete("S", "U")


@pytest.mark.parametrize(("sdk_error", "expected"), SDK_ERRORS)
def test_complete_translates_sdk_errors_without_leaking_details(sdk_error: Exception, expected: str) -> None:
    provider, _ = _provider(_raiser(sdk_error))

    with pytest.raises(LLMProviderError, match=expected) as caught:
        provider.complete("S", "U")

    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is sdk_error


# --- stream() ---------------------------------------------------------------------------------


def test_stream_yields_only_text_deltas_and_fills_metrics() -> None:
    chunks = [_chunk("## Esti"), _chunk(""), _chunk("mación"), _chunk(None), _chunk(" final", finish="stop"), _chunk(usage=(200, 45))]
    provider, client = _provider(lambda **_: iter(chunks))
    metrics = GenerationMetrics(model="placeholder")

    assert list(provider.stream("S", "U", metrics=metrics)) == ["## Esti", "mación", " final"]
    assert client.calls[0]["stream"] is True
    assert client.calls[0]["stream_options"] == {"include_usage": True}
    assert (metrics.model, metrics.input_tokens, metrics.output_tokens) == ("gpt-test", 200, 45)
    assert metrics.latency_seconds is not None and metrics.latency_seconds >= 0


def test_stream_works_without_a_metrics_object() -> None:
    provider, _ = _provider(lambda **_: iter([_chunk("hola")]))
    assert list(provider.stream("S", "U")) == ["hola"]


@pytest.mark.parametrize(("sdk_error", "expected"), SDK_ERRORS)
def test_stream_translates_errors_raised_when_opening_the_stream(sdk_error: Exception, expected: str) -> None:
    provider, _ = _provider(_raiser(sdk_error))
    with pytest.raises(LLMProviderError, match=expected):
        list(provider.stream("S", "U"))


def test_stream_translates_errors_raised_mid_stream() -> None:
    def _broken() -> Iterator[SimpleNamespace]:
        yield _chunk("parcial")
        raise openai.APITimeoutError(request=_REQUEST)

    provider, _ = _provider(lambda **_: _broken())
    received: list[str] = []

    with pytest.raises(LLMProviderError, match="tardó demasiado"):
        for token in provider.stream("S", "U"):
            received.append(token)

    assert received == ["parcial"]
