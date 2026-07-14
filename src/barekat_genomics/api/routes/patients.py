"""Patient management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import (
    CurrentUser,
    assert_patient_access,
    get_current_user,
    require_permission,
)
from barekat_genomics.core.audit import client_ip, log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, has_permission, is_physician_role
from barekat_genomics.schemas import PatientCreate, PatientResponse
from barekat_genomics.services.patient_service import PatientService

router = APIRouter(prefix="/patients")


def _require_patient_list(user: CurrentUser) -> None:
    if is_physician_role(user.role):
        if not has_permission(user.role, Permission.PATIENTS_READ_OWN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    elif not has_permission(user.role, Permission.PATIENTS_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(
    data: PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PATIENTS_WRITE)),
) -> PatientResponse:
    service = PatientService(db)
    clinician_id = user.id if is_physician_role(user.role) else None
    patient = service.create(
        data,
        assigned_clinician_id=clinician_id,
        organization_id=user.organization_id,
    )
    log_audit_event(
        db,
        user_id=str(user.id),
        action="create_patient",
        resource_type="patient",
        resource_id=str(patient.id),
        ip_address=client_ip(request),
    )
    return PatientResponse.model_validate(patient)


@router.get("/", response_model=list[PatientResponse])
def list_patients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[PatientResponse]:
    _require_patient_list(user)
    service = PatientService(db)
    patients = service.list_for_user(
        user.id,
        user.role,
        skip=skip,
        limit=limit,
        organization_id=user.organization_id,
    )
    return [PatientResponse.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> PatientResponse:
    service = PatientService(db)
    patient = service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="view_patient",
        resource_type="patient",
        resource_id=str(patient_id),
        ip_address=client_ip(request),
    )
    return PatientResponse.model_validate(patient)
