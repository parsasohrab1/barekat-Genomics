"""Health check و متریک‌های Prometheus."""

from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse

from barekat_genomics import __version__
from barekat_genomics.core.config import get_settings
from barekat_genomics.core.observability.health_checks import (
    aggregate_status,
    checks_to_dict,
    run_health_checks,
)
from barekat_genomics.core.observability.metrics import metrics_payload
from barekat_genomics.schemas import HealthResponse

router = APIRouter()


@router.get("/health/live")
def liveness() -> dict:
    """Liveness probe — API در حال اجراست."""
    return {"status": "alive", "version": __version__}


@router.get("/health/ready")
def readiness(response: Response) -> dict:
    """Readiness probe — وابستگی‌های حیاتی."""
    checks = run_health_checks(include_celery=False)
    overall = aggregate_status(checks)
    if overall == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": overall,
        "version": __version__,
        "services": checks_to_dict(checks),
    }


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response) -> HealthResponse:
    """بررسی کامل سلامت تمام سرویس‌ها."""
    checks = run_health_checks(include_celery=True)
    overall = aggregate_status(checks)
    if overall == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status=overall,
        version=__version__,
        services=checks_to_dict(checks),
    )


@router.get("/metrics")
def prometheus_metrics() -> PlainTextResponse:
    """Endpoint متریک Prometheus."""
    settings = get_settings()
    if not settings.metrics_enabled:
        return PlainTextResponse("metrics disabled", status_code=404)
    return PlainTextResponse(
        content=metrics_payload().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
