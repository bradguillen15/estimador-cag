from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas.estimations import EstimateRequest, EstimateResponse
from app.services.llm_service import LLMService

router = APIRouter(tags=["estimations"])
llm_service = LLMService()


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
