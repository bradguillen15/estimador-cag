"""FastAPI dependency providers (``Depends``); override them in tests via ``dependency_overrides``."""

from functools import lru_cache

from app.config import settings
from app.services.estimation_service import EstimationService
from app.services.llm.factory import get_llm_provider


@lru_cache
def get_estimation_service() -> EstimationService:
    return EstimationService(provider=get_llm_provider(settings))
