from fastapi import FastAPI

from app.routers import estimations

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

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
