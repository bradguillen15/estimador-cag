from fastapi import FastAPI

from app.routers import estimations

app = FastAPI(title="Estimador CAG", version="0.1.0")

app.include_router(estimations.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
