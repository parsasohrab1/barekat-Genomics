"""EHR integration endpoints — FHIR R4، HL7 v2، کانکتورهای بیمارستانی."""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, assert_patient_access, get_current_user
from barekat_genomics.core.audit import log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, has_permission
from barekat_genomics.ehr.import_fhir import parse_fhir_patient_bundle
from barekat_genomics.ehr.import_hl7 import parse_hl7_message
from barekat_genomics.ehr.service import EHRIntegrationService
from barekat_genomics.schemas import (
    EHRConnectorInfo,
    EHRPushRequest,
    EHRPushResponse,
    EHRVariantExport,
)
from barekat_genomics.services.patient_service import PatientService
from barekat_genomics.services.report_service import ReportService

router = APIRouter(prefix="/ehr")


class HL7ImportRequest(BaseModel):
    message: str = Field(min_length=10)


def _check_ehr_permission(user: CurrentUser) -> None:
    if not (
        has_permission(user.role, Permission.EHR_EXPORT)
        or has_permission(user.role, Permission.EHR_EXPORT_OWN)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")


def _load_export(db: Session, patient_id: uuid.UUID, user: CurrentUser) -> tuple:
    _check_ehr_permission(user)
    patient = PatientService(db).get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)

    report_service = ReportService(db)
    export = report_service.export_for_ehr(patient_id)
    if not export:
        raise HTTPException(status_code=404, detail="داده‌ای برای خروجی یافت نشد")

    latest_report = None
    if export.report_id:
        latest_report = report_service.get_report(export.report_id)

    ctx = EHRIntegrationService().build_context(patient, export, latest_report)
    return patient, export, latest_report, ctx


@router.get("/connectors", response_model=list[EHRConnectorInfo])
def list_ehr_connectors(
    user: CurrentUser = Depends(get_current_user),
) -> list[EHRConnectorInfo]:
    _check_ehr_permission(user)
    return [EHRConnectorInfo.model_validate(c) for c in EHRIntegrationService().list_connectors()]


@router.get("/export/{patient_id}", response_model=EHRVariantExport)
def export_to_ehr(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EHRVariantExport:
    _, export, _, _ = _load_export(db, patient_id, user)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_export",
        resource_type="patient",
        resource_id=str(patient_id),
        details="format=json",
        ip_address=request.client.host if request.client else None,
    )
    return export


@router.get("/export/{patient_id}/fhir")
def export_fhir(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    _, export, _, ctx = _load_export(db, patient_id, user)
    bundle = EHRIntegrationService().export_fhir(ctx)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_export",
        resource_type="patient",
        resource_id=str(patient_id),
        details="format=fhir",
        ip_address=request.client.host if request.client else None,
    )
    import json

    return Response(
        content=json.dumps(bundle, ensure_ascii=False),
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="fhir-{export.report_id or patient_id}.json"'},
    )


@router.get("/export/{patient_id}/hl7", response_class=PlainTextResponse)
def export_hl7(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PlainTextResponse:
    _, export, _, ctx = _load_export(db, patient_id, user)
    message = EHRIntegrationService().export_hl7(ctx)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_export",
        resource_type="patient",
        resource_id=str(patient_id),
        details="format=hl7",
        ip_address=request.client.host if request.client else None,
    )
    return PlainTextResponse(
        content=message,
        media_type="application/hl7-v2",
        headers={"Content-Disposition": f'attachment; filename="oru-{export.report_id or patient_id}.hl7"'},
    )


@router.post("/push/{patient_id}", response_model=EHRPushResponse)
def push_to_ehr(
    patient_id: uuid.UUID,
    body: EHRPushRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> EHRPushResponse:
    _, export, _, ctx = _load_export(db, patient_id, user)
    result = EHRIntegrationService().push(ctx, export, body.connector, body.format)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_push",
        resource_type="patient",
        resource_id=str(patient_id),
        details=f"connector={body.connector},format={body.format},success={result.success}",
        ip_address=request.client.host if request.client else None,
    )
    if not result.success:
        raise HTTPException(status_code=502, detail=result.message)
    return EHRPushResponse(
        success=result.success,
        connector=result.connector,
        format=result.format,
        message=result.message,
        external_id=result.external_id,
        details=result.details or None,
    )


@router.post("/import/fhir")
def import_fhir(
    bundle: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if not has_permission(user.role, Permission.EHR_IMPORT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    try:
        parsed = parse_fhir_patient_bundle(bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    patient, created = PatientService(db).upsert_from_ehr(
        external_id=parsed["external_id"],
        full_name=parsed.get("full_name"),
        gender=parsed.get("gender"),
        ehr_patient_id=parsed.get("ehr_patient_id"),
        organization_id=user.organization_id,
        assigned_clinician_id=user.id if user.role in ("physician", "clinician") else None,
    )
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_import",
        resource_type="patient",
        resource_id=str(patient.id),
        details=f"format=fhir,created={created}",
        ip_address=request.client.host if request and request.client else None,
    )
    return {
        "created": created,
        "patient_id": str(patient.id),
        "external_id": patient.external_id,
        "resource_count": parsed.get("resource_count"),
    }


@router.post("/import/hl7")
def import_hl7(
    body: HL7ImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if not has_permission(user.role, Permission.EHR_IMPORT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    try:
        parsed = parse_hl7_message(body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    patient, created = PatientService(db).upsert_from_ehr(
        external_id=parsed["external_id"],
        full_name=parsed.get("full_name"),
        gender=parsed.get("gender"),
        ehr_patient_id=parsed.get("ehr_patient_id"),
        organization_id=user.organization_id,
        assigned_clinician_id=user.id if user.role in ("physician", "clinician") else None,
    )
    log_audit_event(
        db,
        user_id=str(user.id),
        action="ehr_import",
        resource_type="patient",
        resource_id=str(patient.id),
        details=f"format=hl7,created={created},type={parsed.get('message_type')}",
        ip_address=request.client.host if request.client else None,
    )
    return {
        "created": created,
        "patient_id": str(patient.id),
        "external_id": patient.external_id,
        "message_type": parsed.get("message_type"),
    }
