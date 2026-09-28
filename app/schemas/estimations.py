"""Contratos de request/response para el endpoint de estimaciones."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ProjectType(str, Enum):
    MOBILE_APP = "mobile_app"
    WEB_SAAS = "web_saas"
    INTERNAL_TOOL = "internal_tool"
    DATA_PIPELINE = "data_pipeline"


class DetailLevel(str, Enum):
    SUMMARY = "summary"
    MEDIUM = "medium"
    DETAILED = "detailed"


class OutputFormat(str, Enum):
    PHASES_TABLE = "phases_table"
    LINE_ITEMS = "line_items"
    NARRATIVE = "narrative"


class ResponseLanguage(str, Enum):
    """Idioma en el que el modelo debe responder (los prompts siempre están en inglés)."""

    ES = "es"
    EN = "en"


class EstimationRequest(BaseModel):
    description: str = Field(min_length=20, max_length=2000)
    project_type: ProjectType
    detail_level: DetailLevel
    output_format: OutputFormat
    language: ResponseLanguage = ResponseLanguage.ES

    @field_validator("language", mode="before")
    @classmethod
    def _fallback_to_spanish(cls, value: object) -> ResponseLanguage:
        # Lenient on purpose: a missing or unsupported language keeps the original behaviour
        # (Spanish) instead of failing the whole estimation.
        if isinstance(value, str) and value.strip().lower() in ResponseLanguage._value2member_map_:
            return ResponseLanguage(value.strip().lower())
        return ResponseLanguage.ES


class EstimationResponse(BaseModel):
    text: str
    prompt_version: str


class PromptContextResponse(BaseModel):
    prompt_version: str
    examples_markdown: str
