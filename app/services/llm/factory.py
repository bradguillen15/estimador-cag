"""Builds the LLM provider (LiteLLM) from the ``LLM_MODELS`` setting."""

from app.config import Settings
from app.services.llm.base import ModerationProvider, StreamingLLMProvider
from app.services.llm.litellm import LiteLLMProvider
from app.services.llm.moderation import LiteLLMModerator


def _require_key(name: str, value: str | None) -> str:
    """Fails at build time (boot / first use), never in the middle of a request."""
    if not value:
        raise ValueError(f"{name} is required by the configured LLM provider but is not set.")
    return value


def get_llm_provider(settings: Settings) -> StreamingLLMProvider:
    key_by_prefix = {
        "anthropic": ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        "openai": ("OPENAI_API_KEY", settings.openai_api_key),
    }
    if not settings.llm_models:
        raise ValueError("LLM_MODELS must list at least one '<provider>/<model>' entry.")

    api_keys: dict[str, str] = {}
    for model in settings.llm_models:
        prefix = model.split("/", 1)[0]
        if "/" not in model or prefix not in key_by_prefix:
            raise ValueError(
                f"Unsupported LLM_MODELS entry: {model!r}. "
                f"Use '<provider>/<model>' with a provider in: {', '.join(sorted(key_by_prefix))}"
            )
        env_name, key = key_by_prefix[prefix]
        api_keys[prefix] = _require_key(env_name, key)

    return LiteLLMProvider(
        models=settings.llm_models,
        api_keys=api_keys,
        timeout=settings.llm_timeout,
        retries=settings.llm_retries,
        max_tokens=settings.llm_max_tokens,
    )


def get_moderator(settings: Settings) -> ModerationProvider | None:
    """The moderation backend, or ``None`` when ``MODERATION_ENABLED`` is off."""
    if not settings.moderation_enabled:
        return None
    return LiteLLMModerator(api_key=_require_key("OPENAI_API_KEY", settings.openai_api_key))
