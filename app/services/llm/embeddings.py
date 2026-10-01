"""Text embeddings through LiteLLM. Part of the LiteLLM boundary: SDK types never leave this module."""

from collections.abc import Callable
from typing import Any

import litellm


class LiteLLMEmbedder:
    """Implements ``EmbeddingProvider``."""

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: float = 10,
        embedding: Callable[..., Any] | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._embedding = embedding

    def embed(self, text: str) -> list[float]:
        embedding = self._embedding or litellm.embedding
        response = embedding(model=self._model, input=[text], api_key=self._api_key, timeout=self._timeout)
        return [float(value) for value in response.data[0]["embedding"]]
