"""Servicio de llamada al LLM (lógica de negocio)."""

from app.config import settings


class LLMService:
    def __init__(self) -> None:
        self.model = settings.openai_model
        self.api_key = settings.openai_api_key

    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Paso siguiente: implementar llamada al proveedor LLM")
