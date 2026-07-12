"""Pipeline processing endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from barekat_genomics.core.database import get_db
from barekat_genomics.schemas import PipelineJobCreate, PipelineJobResponse
from barekat_genomics.services.pipeline_service import PipelineService

router = APIRouter(prefix="/pipeline")


@router.post("/run", response_model=PipelineJobResponse, status_code=202)
def start_pipeline(
    data: PipelineJobCreate,
    db: Session = Depends(get_db),
) -> PipelineJobResponse:
    service = PipelineService(db)
    try:
        job = service.start_pipeline(data.sample_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PipelineJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=PipelineJobResponse)
def get_pipeline_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> PipelineJobResponse:
    service = PipelineService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    return PipelineJobResponse.model_validate(job)
