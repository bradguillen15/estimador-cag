from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.concurrency import iterate_in_threadpool

from app.dependencies import get_estimation_service
from app.exceptions import EstimationError
from app.schemas.estimations import (
    EstimationRequest,
    EstimationResponse,
    PromptContextResponse,
)
from app.services.estimation_service import PROMPT_VERSION, EstimationService
from app.services.llm.base import GenerationMetrics

logger = structlog.get_logger()

router = APIRouter(tags=["estimations"])

Service = Annotated[EstimationService, Depends(get_estimation_service)]

_UNEXPECTED_STREAM_ERROR = "Error inesperado al generar la estimación."


@router.get("/context", response_model=PromptContextResponse)
def get_prompt_context(service: Service) -> PromptContextResponse:
    return PromptContextResponse(
        prompt_version=PROMPT_VERSION,
        examples_markdown=service.context_examples(),
    )


# Domain errors are mapped to HTTP status codes by the exception handlers in main.py.
@router.post("/estimate", response_model=EstimationResponse)
def create_estimate(body: EstimationRequest, service: Service) -> EstimationResponse:
    text = service.generate(body)
    return EstimationResponse(text=text, prompt_version=PROMPT_VERSION)


@router.post("/estimate/stream", response_class=EventSourceResponse)
async def create_estimate_stream(
    body: EstimationRequest,
    request: Request,
    service: Service,
) -> AsyncIterator[ServerSentEvent]:
    metrics = GenerationMetrics(model=service.model)

    # The HTTP status is already 200 once streaming starts, so failures travel as an `error` event.
    try:
        stream = service.generate_stream(body, metrics=metrics)
        async for token in iterate_in_threadpool(stream):
            if await request.is_disconnected():
                break
            yield ServerSentEvent(data=token, event="token")
        else:
            yield ServerSentEvent(
                data={
                    "model": metrics.model,
                    "provider": service.provider_name,
                    "input_tokens": metrics.input_tokens,
                    "output_tokens": metrics.output_tokens,
                    "latency_seconds": metrics.latency_seconds,
                    "prompt_version": PROMPT_VERSION,
                },
                event="done",
            )
    except EstimationError as exc:
        yield ServerSentEvent(data={"detail": str(exc)}, event="error")
    except Exception:
        logger.exception("estimate_stream_failed")
        yield ServerSentEvent(data={"detail": _UNEXPECTED_STREAM_ERROR}, event="error")
