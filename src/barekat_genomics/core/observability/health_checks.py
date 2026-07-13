"""بررسی سلامت وابستگی‌ها برای production."""

from __future__ import annotations

import time
from dataclasses import dataclass

import structlog
from sqlalchemy import text

from barekat_genomics.core.config import get_settings
from barekat_genomics.core.database import engine

logger = structlog.get_logger(__name__)


@dataclass
class ServiceHealth:
    name: str
    status: str  # up | down | degraded
    latency_ms: float | None = None
    detail: str | None = None


def check_database() -> ServiceHealth:
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ms = (time.perf_counter() - start) * 1000
        return ServiceHealth("database", "up", round(ms, 2))
    except Exception as exc:
        logger.warning("health_check_database_failed", error=str(exc))
        return ServiceHealth("database", "down", detail=str(exc))


def check_redis() -> ServiceHealth:
    start = time.perf_counter()
    try:
        import redis

        settings = get_settings()
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        ms = (time.perf_counter() - start) * 1000
        return ServiceHealth("redis", "up", round(ms, 2))
    except Exception as exc:
        logger.warning("health_check_redis_failed", error=str(exc))
        return ServiceHealth("redis", "down", detail=str(exc))


def check_storage() -> ServiceHealth:
    start = time.perf_counter()
    try:
        from barekat_genomics.core.storage import get_storage

        storage = get_storage()
        storage.ensure_bucket()
        ms = (time.perf_counter() - start) * 1000
        return ServiceHealth("storage", "up", round(ms, 2))
    except Exception as exc:
        logger.warning("health_check_storage_failed", error=str(exc))
        return ServiceHealth("storage", "degraded", detail=str(exc))


def check_celery() -> ServiceHealth:
    try:
        from barekat_genomics.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=2.0)
        ping = inspector.ping()
        if ping:
            return ServiceHealth("celery", "up", detail=f"{len(ping)} worker(s)")
        return ServiceHealth("celery", "degraded", detail="no workers responding")
    except Exception as exc:
        return ServiceHealth("celery", "degraded", detail=str(exc))


def run_health_checks(*, include_celery: bool = True) -> list[ServiceHealth]:
    checks = [check_database(), check_redis(), check_storage()]
    if include_celery:
        checks.append(check_celery())
    return checks


def aggregate_status(checks: list[ServiceHealth]) -> str:
    if any(c.status == "down" for c in checks if c.name in ("database", "redis")):
        return "unhealthy"
    if any(c.status in ("down", "degraded") for c in checks):
        return "degraded"
    return "healthy"


def checks_to_dict(checks: list[ServiceHealth]) -> dict[str, str]:
    return {c.name: c.status for c in checks}
