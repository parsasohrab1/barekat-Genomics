"""Audit log endpoints (admin only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.models.audit import AuditLog
from barekat_genomics.schemas import AuditLogResponse

router = APIRouter(prefix="/audit")


@router.get("/logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.AUDIT_READ)),
) -> list[AuditLogResponse]:
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [AuditLogResponse.model_validate(log) for log in logs]
