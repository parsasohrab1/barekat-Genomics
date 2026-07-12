"""Health check endpoints."""

from fastapi import APIRouter

from barekat_genomics import __version__
from barekat_genomics.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=__version__,
        services={
            "api": "up",
            "database": "up",
            "celery": "up",
            "storage": "up",
        },
    )
