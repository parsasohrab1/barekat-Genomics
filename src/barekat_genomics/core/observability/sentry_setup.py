"""راه‌اندازی Sentry برای ردیابی exception."""

from __future__ import annotations

import structlog

from barekat_genomics.core.config import get_settings

logger = structlog.get_logger(__name__)


def init_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logger.warning("sentry_sdk not installed — skipping Sentry init")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.sentry_release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        before_send=_scrub_phi,
    )
    logger.info("sentry_initialized", environment=settings.app_env)


def _scrub_phi(event: dict, _hint: dict) -> dict | None:
    """حذف فیلدهای حساس قبل از ارسال به Sentry."""
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            for key in ("password", "name", "clinical_notes", "encrypted_name"):
                data.pop(key, None)
    return event


def capture_exception(exc: BaseException, **context) -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        pass
