from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider keys are optional: only the providers actually in use need one (checked by the factory).
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    # Single source of truth for the model and the fallback order: ordered "<provider>/<model>" list (first = primary, the rest = fallbacks).
    # NoDecode lets LLM_MODELS be a plain comma-separated string instead of JSON.
    llm_models: Annotated[list[str], NoDecode] = [
        "anthropic/claude-sonnet-5-5",
        "openai/gpt-4o-mini",
    ]
    llm_timeout: float = 30
    llm_retries: int = 2
    llm_max_tokens: int = 16000
    app_env: str
    log_level: str

    @field_validator("llm_models", mode="before")
    @classmethod
    def _split_llm_models(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
