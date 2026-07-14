"""لاگ ممیزی دسترسی به داده‌های حساس (HIPAA)."""

from __future__ import annotations

import structlog
from fastapi import Request
from sqlalchemy.orm import Session

from barekat_genomics.core.config import get_settings
from barekat_genomics.models.audit import AuditLog

logger = structlog.get_logger(__name__)


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def log_audit_event(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> None:
    """ثبت رویداد ممیزی در پایگاه داده — خطا نباید جریان اصلی را متوقف کند."""
    settings = get_settings()
    if not settings.audit_log_enabled:
        logger.debug(
            "audit_event_skipped",
            action=action,
            resource_type=resource_type,
            reason="audit_log_disabled",
        )
        return

    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(
            "audit_event_failed",
            action=action,
            resource_type=resource_type,
            error=str(exc),
        )
        return

    logger.info(
        "audit_event",
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )
