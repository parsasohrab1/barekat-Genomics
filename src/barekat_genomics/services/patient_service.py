"""سرویس مدیریت بیماران."""

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.core.security import encrypt_phi
from barekat_genomics.models.patient import Patient
from barekat_genomics.schemas import PatientCreate


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: PatientCreate) -> Patient:
        patient = Patient(
            external_id=data.external_id,
            encrypted_name=encrypt_phi(data.name) if data.name else None,
            age=data.age,
            gender=data.gender,
            clinical_notes=data.clinical_notes,
            ehr_patient_id=data.ehr_patient_id,
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_by_ehr_id(self, ehr_patient_id: str) -> Patient | None:
        return self.db.query(Patient).filter(Patient.ehr_patient_id == ehr_patient_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Patient]:
        return self.db.query(Patient).offset(skip).limit(limit).all()
