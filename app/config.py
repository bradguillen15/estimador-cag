from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    open_api_key: str
    antropic_api_key: str
    llm_provider: str
    llm_model: str
    app_env: str
    log_level: str


settings = Settings()
