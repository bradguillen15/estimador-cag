"""Contrato de los proveedores LLM.

Todo proveedor devuelve texto y, ante cualquier fallo, lanza ``LLMProviderError``
(nunca ``None`` ni un string vacío). Los tipos del SDK no salen de su módulo.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass
class GenerationMetrics:
    """Métricas de la última llamada al LLM (rellenadas al terminar el stream)."""

    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_seconds: float | None = None


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
