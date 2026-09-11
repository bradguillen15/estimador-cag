from fastapi import APIRouter

router = APIRouter(prefix="/estimations", tags=["estimations"])


@router.get("/")
def list_estimations() -> dict[str, str]:
    return {"message": "estimations router ready"}
