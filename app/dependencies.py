"""FastAPI dependency providers (``Depends``); override them in tests via ``dependency_overrides``."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Query

from app.config import settings
from app.exceptions import UnknownPromptVersionError
from app.prompts.loader import PROMPT_VERSION, available_prompt_versions
from app.schemas.estimations import EstimationRequest
from app.services.cache.factory import get_response_cache
from app.services.cache.semantic import NoOpSemanticCache, SemanticCache, build_semantic_cache
from app.services.estimation_service import EstimationService
from app.services.guardrails.input import InputGuardrails
from app.services.llm.factory import get_embedder, get_llm_provider, get_moderator


def _get_semantic_cache() -> SemanticCache:
    if not settings.semantic_cache_enabled:
        return NoOpSemanticCache()
    return build_semantic_cache(settings, get_embedder(settings), settings.llm_models)


@lru_cache
def get_estimation_service() -> EstimationService:
    return EstimationService(
        provider=get_llm_provider(settings),
        guardrails=InputGuardrails(moderator=get_moderator(settings)),
        cache=get_response_cache(settings),
        semantic_cache=_get_semantic_cache(),
        cache_models=tuple(settings.llm_models),
    )


def get_prompt_version(
    prompt_version: Annotated[
        str | None,
        Query(description="Prompt version to run (a folder under app/prompts/estimation/). Defaults to the active one."),
    ] = None,
) -> str:
    """The effective prompt version; unknown or malformed values are an HTTP 422 before any other work.

    Checked against the versions found on disk, so values such as ``../x`` never reach the loader.
    """
    if prompt_version is None:
        return PROMPT_VERSION
    if prompt_version not in available_prompt_versions():
        available = ", ".join(available_prompt_versions())
        raise UnknownPromptVersionError(
            f"Versión de prompt desconocida: usa una de {available}."
        )
    return prompt_version


def get_safe_request(
    body: EstimationRequest,
    service: Annotated[EstimationService, Depends(get_estimation_service)],
    _prompt_version: Annotated[str, Depends(get_prompt_version)],
) -> EstimationRequest:
    """The request after the input guardrails.

    A dependency runs before the endpoint (and before any streaming response starts), so a
    rejection is a plain HTTP 400 on both ``/estimate`` and ``/estimate/stream``. The prompt
    version is validated first, so an invalid one never reaches the guardrails.
    """
    return service.prepare(body)
