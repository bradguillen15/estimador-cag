"""LiteLLM moderation adapter and its factory (LiteLLM itself is never called)."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.config import Settings
from app.services.llm.factory import get_moderator
from app.services.llm.moderation import LiteLLMModerator


def _response(*results: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        results=[SimpleNamespace(flagged=r["flagged"], categories=r.get("categories", {})) for r in results]
    )


def test_returns_the_flagged_categories() -> None:
    calls: list[dict[str, Any]] = []

    def fake_moderation(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return _response({"flagged": True, "categories": {"violence": True, "hate": False, "sexual": True}})

    moderator = LiteLLMModerator(api_key="k", moderation=fake_moderation)

    assert moderator.flagged_categories("texto") == ["sexual", "violence"]
    assert calls == [{"input": "texto", "model": "omni-moderation-latest", "api_key": "k"}]


def test_clean_text_has_no_categories() -> None:
    moderator = LiteLLMModerator(api_key="k", moderation=lambda **_: _response({"flagged": False}))
    assert moderator.flagged_categories("texto") == []


def test_flagged_without_categories_is_reported_as_unspecified() -> None:
    moderator = LiteLLMModerator(api_key="k", moderation=lambda **_: _response({"flagged": True}))
    assert moderator.flagged_categories("texto") == ["unspecified"]


def test_sdk_errors_propagate_so_the_guardrail_can_fail_open() -> None:
    def boom(**_: Any) -> None:
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        LiteLLMModerator(api_key="k", moderation=boom).flagged_categories("texto")


def test_factory_builds_a_moderator_only_when_enabled() -> None:
    assert get_moderator(Settings(app_env="t", log_level="INFO", moderation_enabled=False)) is None
    enabled = Settings(app_env="t", log_level="INFO", moderation_enabled=True, openai_api_key="k")
    assert isinstance(get_moderator(enabled), LiteLLMModerator)


def test_factory_requires_the_openai_key_when_enabled() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_moderator(Settings(app_env="t", log_level="INFO", moderation_enabled=True, openai_api_key=None))
