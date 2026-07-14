"""API انطباق رگولاتوری و حقوق سوژه داده."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, assert_patient_access, get_current_user, require_permission
from barekat_genomics.compliance.checklist import checklist_as_dicts, summary_counts
from barekat_genomics.core.audit import client_ip, log_audit_event
from barekat_genomics.core.config import get_settings
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.core.security import decrypt_phi
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.services.patient_service import PatientService

router = APIRouter(prefix="/compliance")


@router.get("/checklist")
def get_checklist(
    _: CurrentUser = Depends(require_permission(Permission.COMPLIANCE_READ)),
) -> dict:
    return {
        "summary": summary_counts(),
        "items": checklist_as_dicts(),
        "phi_retention_days": get_settings().phi_retention_days,
        "regulators": ["GDPR-like", "MOH", "HIPAA"],
    }


@router.get("/subjects/{patient_id}/export")
def export_subject_data(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.COMPLIANCE_MANAGE)),
) -> dict:
    """حق دسترسی / حمل‌پذیری داده بیمار (GDPR-like Art.15/20)."""
    patient = PatientService(db).get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)

    name = None
    if patient.encrypted_name:
        try:
            name = decrypt_phi(patient.encrypted_name)
        except Exception:
            name = "[encrypted]"

    samples = db.query(SequencingSample).filter(SequencingSample.patient_id == patient_id).all()
    reports = db.query(GenomicReport).filter(GenomicReport.patient_id == patient_id).all()
    payload = {
        "patient": {
            "id": str(patient.id),
            "external_id": patient.external_id,
            "name": name,
            "age": patient.age,
            "gender": patient.gender,
            "ehr_patient_id": patient.ehr_patient_id,
            "organization_id": str(patient.organization_id) if patient.organization_id else None,
        },
        "samples": [
            {"id": str(s.id), "sample_id": s.sample_id, "status": s.status, "file_type": s.file_type}
            for s in samples
        ],
        "reports": [
            {"id": str(r.id), "status": r.status, "report_type": r.report_type, "summary": r.summary}
            for r in reports
        ],
    }
    log_audit_event(
        db,
        user_id=str(user.id),
        action="subject_access_export",
        resource_type="patient",
        resource_id=str(patient_id),
        ip_address=client_ip(request),
    )
    return payload


@router.post("/subjects/{patient_id}/erase")
def erase_subject_phi(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.COMPLIANCE_MANAGE)),
) -> dict:
    """ناشناس‌سازی نسبی PHI (حق فراموشی نسبی — نگهداشت نتایج بالینی در صورت الزام قانونی)."""
    patient = PatientService(db).get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)

    patient.encrypted_name = None
    patient.clinical_notes = None
    patient.ehr_patient_id = None
    db.commit()
    log_audit_event(
        db,
        user_id=str(user.id),
        action="subject_erase_phi",
        resource_type="patient",
        resource_id=str(patient_id),
        ip_address=client_ip(request),
    )
    return {"status": "anonymized", "patient_id": str(patient_id)}
