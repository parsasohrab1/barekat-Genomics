"""دستیار پشتیبان تصمیم — خلاصه ساده و پرسش واریانت."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, assert_patient_access, get_current_user
from barekat_genomics.core.audit import log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, has_permission
from barekat_genomics.models.patient import Patient
from barekat_genomics.schemas import PlainSummaryResponse, VariantAskRequest, VariantAskResponse
from barekat_genomics.services.ai_service import AIAssistService
from barekat_genomics.ai.disclaimer import FULL_DISCLAIMER_FA

router = APIRouter(prefix="/ai")


def _require_ai_assist(user: CurrentUser) -> None:
    if not has_permission(user.role, Permission.AI_ASSIST):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی به دستیار مجاز نیست")


@router.get("/disclaimer")
def get_disclaimer() -> dict:
    return {
        "disclaimer": FULL_DISCLAIMER_FA,
        "decision_support_only": True,
    }


@router.post("/reports/{report_id}/plain-summary", response_model=PlainSummaryResponse)
def plain_summary(
    report_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PlainSummaryResponse:
    _require_ai_assist(user)
    service = AIAssistService(db)
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="دستیار پشتیبان تصمیم غیرفعال است")

    report = service.reports.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")

    if has_permission(user.role, Permission.REPORTS_READ_OWN) and not has_permission(
        user.role, Permission.REPORTS_READ
    ):
        patient = db.query(Patient).filter(Patient.id == report.patient_id).first()
        if patient:
            assert_patient_access(user, patient)

    try:
        result = service.plain_summary_for_report(report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    log_audit_event(
        db,
        user_id=str(user.id),
        action="ai_plain_summary",
        resource_type="report",
        resource_id=str(report_id),
        ip_address=request.client.host if request.client else None,
    )
    return PlainSummaryResponse(**result)


@router.post("/variants/ask", response_model=VariantAskResponse)
def ask_variant(
    data: VariantAskRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> VariantAskResponse:
    _require_ai_assist(user)
    service = AIAssistService(db)
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="دستیار پشتیبان تصمیم غیرفعال است")

    if not data.variant_id and not data.rs_id:
        raise HTTPException(
            status_code=400,
            detail="variant_id یا rs_id الزامی است",
        )

    try:
        result = service.ask_about_variant(
            data.question,
            variant_id=data.variant_id,
            rs_id=data.rs_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    log_audit_event(
        db,
        user_id=str(user.id),
        action="ai_variant_ask",
        resource_type="variant",
        resource_id=str(data.variant_id) if data.variant_id else data.rs_id,
        details=data.question[:500],
        ip_address=request.client.host if request.client else None,
    )
    return VariantAskResponse(**result)
