"""Sequencing sample endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from barekat_genomics.core.database import get_db
from barekat_genomics.core.storage import get_storage
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.schemas import SampleResponse
from barekat_genomics.services.patient_service import PatientService

router = APIRouter(prefix="/samples")


@router.post("/upload", response_model=SampleResponse, status_code=201)
async def upload_sample(
    patient_id: uuid.UUID = Form(...),
    sample_id: str = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> SampleResponse:
    if file_type not in ("FASTQ", "BAM"):
        raise HTTPException(status_code=400, detail="نوع فایل باید FASTQ یا BAM باشد")

    patient_service = PatientService(db)
    if not patient_service.get_by_id(patient_id):
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")

    storage = get_storage()
    object_key = f"samples/{patient_id}/{sample_id}/{file.filename}"
    content = await file.read()
    storage_path = storage.upload_bytes(content, object_key)

    sample = SequencingSample(
        patient_id=patient_id,
        sample_id=sample_id,
        file_type=file_type,
        storage_path=storage_path,
        status="uploaded",
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return SampleResponse.model_validate(sample)


@router.get("/{sample_id}", response_model=SampleResponse)
def get_sample(sample_id: uuid.UUID, db: Session = Depends(get_db)) -> SampleResponse:
    sample = db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="نمونه یافت نشد")
    return SampleResponse.model_validate(sample)
