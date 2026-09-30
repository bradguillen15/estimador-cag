"""FastAPI dependency providers (``Depends``); override them in tests via ``dependency_overrides``."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.schemas.estimations import EstimationRequest
from app.services.cache.factory import get_response_cache
from app.services.estimation_service import EstimationService
from app.services.guardrails.input import InputGuardrails
from app.services.llm.factory import get_llm_provider, get_moderator


@lru_cache
def get_estimation_service() -> EstimationService:
    return EstimationService(
        provider=get_llm_provider(settings),
        guardrails=InputGuardrails(moderator=get_moderator(settings)),
        cache=get_response_cache(settings),
        cache_models=tuple(settings.llm_models),
    )


def get_safe_request(
    body: EstimationRequest,
    service: Annotated[EstimationService, Depends(get_estimation_service)],
) -> EstimationRequest:
    """The request after the input guardrails.

    A dependency runs before the endpoint (and before any streaming response starts), so a
    rejection is a plain HTTP 400 on both ``/estimate`` and ``/estimate/stream``.
    """
    return service.prepare(body)
