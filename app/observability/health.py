from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """Liveness probe — just confirms the process is up. No dependencies checked."""
    return {"status": "ok"}
