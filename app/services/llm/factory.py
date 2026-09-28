"""Selección del proveedor LLM a partir de ``LLM_PROVIDER``."""

from collections.abc import Callable

from app.config import Settings
from app.services.llm.base import StreamingLLMProvider
from app.services.llm.openai import OpenAIProvider

_PROVIDERS: dict[str, Callable[[Settings], StreamingLLMProvider]] = {
    "openai": lambda settings: OpenAIProvider(
        api_key=settings.open_api_key,
        model=settings.llm_model,
    ),
}


def get_llm_provider(settings: Settings) -> StreamingLLMProvider:
    try:
        build = _PROVIDERS[settings.llm_provider.strip().lower()]
    except KeyError:
        raise ValueError(
            f"LLM_PROVIDER no soportado: {settings.llm_provider!r}. "
            f"Opciones: {', '.join(sorted(_PROVIDERS))}"
        ) from None
    return build(settings)
