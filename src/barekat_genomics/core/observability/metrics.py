"""متریک‌های Prometheus برای پایپ‌لاین و API."""

from __future__ import annotations

import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest

# --- Pipeline ---
PIPELINE_JOBS_TOTAL = Counter(
    "barekat_pipeline_jobs_total",
    "تعداد کل jobهای پایپ‌لاین",
    ["status", "priority", "backend"],
)

PIPELINE_DURATION_SECONDS = Histogram(
    "barekat_pipeline_duration_seconds",
    "مدت زمان اجرای پایپ‌لاین (ثانیه)",
    ["status", "priority", "backend"],
    buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600, 7200),
)

PIPELINE_ACTIVE_JOBS = Gauge(
    "barekat_pipeline_active_jobs",
    "jobهای در حال اجرا",
    ["priority"],
)

QC_CHECKS_TOTAL = Counter(
    "barekat_qc_checks_total",
    "نتایج کنترل کیفیت",
    ["result"],
)

PIPELINE_STAGE_ERRORS_TOTAL = Counter(
    "barekat_pipeline_stage_errors_total",
    "خطاهای پایپ‌لاین به تفکیک مرحله",
    ["stage", "error_type"],
)

VARIANTS_CALLED_TOTAL = Counter(
    "barekat_variants_called_total",
    "واریانت‌های شناسایی‌شده",
    ["priority"],
)

# --- API ---
HTTP_REQUESTS_TOTAL = Counter(
    "barekat_http_requests_total",
    "درخواست‌های HTTP",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "barekat_http_request_duration_seconds",
    "مدت زمان درخواست HTTP",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

APP_INFO = Info("barekat_app", "اطلاعات اپلیکیشن")


def init_app_info(version: str, env: str) -> None:
    APP_INFO.info({"version": version, "environment": env})


def metrics_payload() -> bytes:
    return generate_latest()


def record_pipeline_start(priority: str) -> None:
    PIPELINE_ACTIVE_JOBS.labels(priority=priority).inc()


def record_pipeline_finish(
    *,
    status: str,
    priority: str,
    backend: str,
    duration_seconds: float,
    variant_count: int = 0,
) -> None:
    PIPELINE_ACTIVE_JOBS.labels(priority=priority).dec()
    PIPELINE_JOBS_TOTAL.labels(status=status, priority=priority, backend=backend).inc()
    PIPELINE_DURATION_SECONDS.labels(status=status, priority=priority, backend=backend).observe(
        duration_seconds
    )
    if status == "completed" and variant_count:
        VARIANTS_CALLED_TOTAL.labels(priority=priority).inc(variant_count)


def record_qc_result(passed: bool) -> None:
    QC_CHECKS_TOTAL.labels(result="passed" if passed else "failed").inc()


def record_pipeline_error(stage: str, error_type: str = "unknown") -> None:
    PIPELINE_STAGE_ERRORS_TOTAL.labels(stage=stage, error_type=error_type).inc()


@contextmanager
def track_pipeline(priority: str, backend: str):
    record_pipeline_start(priority)
    start = time.perf_counter()
    outcome = {"status": "failed", "variant_count": 0}
    try:
        yield outcome
    finally:
        record_pipeline_finish(
            status=outcome["status"],
            priority=priority,
            backend=backend,
            duration_seconds=time.perf_counter() - start,
            variant_count=outcome.get("variant_count", 0),
        )
