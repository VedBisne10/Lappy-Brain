
from fastapi import APIRouter, Depends
from backend.config import settings
from backend.api.dependencies import get_settings



router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(
    settings: Settings = Depends(get_settings),
):
    """Check whether the LappyBrain API is running."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
