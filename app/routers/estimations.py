from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.concurrency import iterate_in_threadpool

from app.schemas.estimations import (
    EstimationRequest,
    EstimationResponse,
    EstimateStreamRequest,
)
from app.services.llm_service import GenerationMetrics, LLMService, PROMPT_VERSION

router = APIRouter(tags=["estimations"])
llm_service = LLMService()


@router.post("/estimate", response_model=EstimationResponse)
def create_estimate(body: EstimationRequest) -> EstimationResponse:
    try:
        text = llm_service.generate_from_request(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al generar la estimación con el proveedor LLM: {exc}",
        ) from exc

    return EstimationResponse(text=text, prompt_version=PROMPT_VERSION)


@router.post("/estimate/stream", response_class=EventSourceResponse)
async def create_estimate_stream(
    body: EstimateStreamRequest,
    request: Request,
) -> AsyncIterator[ServerSentEvent]:
    messages = [
        {"role": message.role, "content": message.content} for message in body.messages
    ]
    metrics = GenerationMetrics(model=llm_service.model)

    try:
        stream = llm_service.generate_stream(messages, metrics=metrics)
        async for token in iterate_in_threadpool(stream):
            if await request.is_disconnected():
                break
            # data= JSON-encodes the string so spaces/newlines survive the SSE wire
            yield ServerSentEvent(data=token, event="token")
        else:
            yield ServerSentEvent(
                data={
                    "model": metrics.model,
                    "provider": llm_service.provider,
                    "input_tokens": metrics.input_tokens,
                    "output_tokens": metrics.output_tokens,
                    "latency_seconds": metrics.latency_seconds,
                },
                event="done",
            )
    except ValueError as exc:
        yield ServerSentEvent(data={"detail": str(exc)}, event="error")
    except Exception as exc:
        yield ServerSentEvent(data={"detail": str(exc)}, event="error")
