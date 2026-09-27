from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.logging_config import configure_logging
from app.routers import estimations

configure_logging()

app = FastAPI(
    title="Estimador CAG",
    description=(
        "API de estimación de proyectos de software con CAG "
        "(Cache-Augmented Generation). Recibe la transcripción de una reunión "
        "con el cliente y genera una estimación de esfuerzo usando ejemplos "
        "históricos inyectados en el prompt."
    ),
    version="0.1.0",
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=str(uuid4()),
            endpoint=request.url.path,
        )
        try:
            return await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()


app.add_middleware(RequestContextMiddleware)
app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
