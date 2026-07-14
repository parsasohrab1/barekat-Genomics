"""سرویس مدیریت بیماران با ایزولاسیون سازمانی."""

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.core.rbac import is_privileged_role
from barekat_genomics.core.security import encrypt_phi
from barekat_genomics.models.patient import Patient
from barekat_genomics.schemas import PatientCreate


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        data: PatientCreate,
        assigned_clinician_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> Patient:
        patient = Patient(
            organization_id=organization_id,
            external_id=data.external_id,
            encrypted_name=encrypt_phi(data.name) if data.name else None,
            age=data.age,
            gender=data.gender,
            clinical_notes=data.clinical_notes,
            ehr_patient_id=data.ehr_patient_id,
            assigned_clinician_id=assigned_clinician_id,
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def upsert_from_ehr(
        self,
        *,
        external_id: str,
        full_name: str | None,
        gender: str | None,
        ehr_patient_id: str | None,
        organization_id: uuid.UUID | None,
        assigned_clinician_id: uuid.UUID | None = None,
    ) -> tuple[Patient, bool]:
        q = self.db.query(Patient).filter(Patient.external_id == external_id)
        if organization_id is not None:
            q = q.filter(Patient.organization_id == organization_id)
        patient = q.first()
        created = False
        if patient is None:
            patient = Patient(
                organization_id=organization_id,
                external_id=external_id,
                encrypted_name=encrypt_phi(full_name) if full_name else None,
                gender=gender,
                ehr_patient_id=ehr_patient_id,
                assigned_clinician_id=assigned_clinician_id,
            )
            self.db.add(patient)
            created = True
        else:
            if full_name:
                patient.encrypted_name = encrypt_phi(full_name)
            if gender:
                patient.gender = gender
            if ehr_patient_id:
                patient.ehr_patient_id = ehr_patient_id
        self.db.commit()
        self.db.refresh(patient)
        return patient, created

    def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_by_ehr_id(self, ehr_patient_id: str) -> Patient | None:
        return self.db.query(Patient).filter(Patient.ehr_patient_id == ehr_patient_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Patient]:
        return self.db.query(Patient).offset(skip).limit(limit).all()

    def list_for_user(
        self,
        user_id: uuid.UUID,
        role: str,
        skip: int = 0,
        limit: int = 100,
        organization_id: uuid.UUID | None = None,
    ) -> list[Patient]:
        query = self.db.query(Patient)
        if organization_id is not None:
            query = query.filter(Patient.organization_id == organization_id)
        if not is_privileged_role(role):
            query = query.filter(Patient.assigned_clinician_id == user_id)
        return query.offset(skip).limit(limit).all()
