"""Content moderation through LiteLLM (OpenAI moderation endpoint).

Part of the LiteLLM boundary: SDK types never leave this module.
"""

from collections.abc import Callable
from typing import Any

import litellm

DEFAULT_MODERATION_MODEL = "omni-moderation-latest"


class LiteLLMModerator:
    """Implements ``ModerationProvider``. Errors propagate: the caller decides to fail open."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODERATION_MODEL,
        moderation: Callable[..., Any] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._moderation = moderation

    def flagged_categories(self, text: str) -> list[str]:
        moderation = self._moderation or litellm.moderation
        response = moderation(input=text, model=self._model, api_key=self._api_key)
        flagged: set[str] = set()
        for result in response.results:
            if not getattr(result, "flagged", False):
                continue
            categories = getattr(result, "categories", None) or {}
            if hasattr(categories, "model_dump"):
                categories = categories.model_dump()
            flagged.update(name for name, is_flagged in dict(categories).items() if is_flagged)
            if not flagged:
                flagged.add("unspecified")
        return sorted(flagged)
