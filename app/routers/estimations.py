from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import LLMService

router = APIRouter(tags=["estimations"])
llm_service = LLMService()


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

@router.post("/estimate", response_model=EstimateResponse)
def create_estimate(body: EstimateRequest) -> EstimateResponse:
    try:
        estimation = llm_service.generate(body.transcription)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al generar la estimación con el proveedor LLM: {exc}",
        ) from exc

    return EstimateResponse(
        estimation=estimation,
        model=llm_service.model,
        provider=llm_service.provider,
        created_at=datetime.now(timezone.utc),
    )
