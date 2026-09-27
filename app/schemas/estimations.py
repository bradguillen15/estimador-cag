"""Contratos de request/response para el endpoint de estimaciones."""

from datetime import datetime

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    transcription: str = Field(
        ...,
        min_length=1,
        description="Texto de la transcripción de la reunión a estimar",
        examples=[
            "En la reunión con el cliente se discutió la necesidad de una plataforma web..."
        ],
    )


class EstimateResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    created_at: datetime
