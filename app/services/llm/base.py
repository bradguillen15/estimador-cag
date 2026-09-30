"""LLM provider contract.

Every provider returns text and raises ``LLMProviderError`` on any failure (never ``None``
or an empty string). SDK types never leave the provider's own module.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass
class GenerationMetrics:
    """Metrics of the last LLM call (filled in when the stream finishes)."""

    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_seconds: float | None = None
    cached_tokens: int | None = None
    cost_usd: float | None = None


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class StreamingLLMProvider(LLMProvider, Protocol):
    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        metrics: GenerationMetrics | None = None,
    ) -> Iterator[str]: ...
