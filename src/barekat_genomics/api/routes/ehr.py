"""EHR integration endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from barekat_genomics.core.audit import log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.schemas import EHRVariantExport
from barekat_genomics.services.report_service import ReportService

router = APIRouter(prefix="/ehr")


@router.get("/export/{patient_id}", response_model=EHRVariantExport)
def export_to_ehr(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> EHRVariantExport:
    service = ReportService(db)
    export = service.export_for_ehr(patient_id)
    if not export:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")

    log_audit_event(
        db,
        user_id=None,
        action="ehr_export",
        resource_type="patient",
        resource_id=str(patient_id),
        ip_address=request.client.host if request.client else None,
    )
    return export
