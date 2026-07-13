"""Pipeline processing endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.modules.registry import list_modules
from barekat_genomics.schemas import (
    ModuleInfo,
    PipelineJobCreate,
    PipelineJobListItem,
    PipelineJobResponse,
)
from barekat_genomics.services.pipeline_service import PipelineService, compute_job_progress

router = APIRouter(prefix="/pipeline")


@router.get("/modules", response_model=list[ModuleInfo])
def list_diagnostic_modules(
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> list[ModuleInfo]:
    return [
        ModuleInfo(
            id=m.id,
            name_fa=m.name_fa,
            name_en=m.name_en,
            description_fa=m.description_fa,
            category=m.category,
            gene_count=len(m.genes),
            requires_paired_sample=m.requires_paired_sample,
            cpic_guideline=m.cpic_guideline,
        )
        for m in list_modules()
    ]


@router.get("/jobs", response_model=list[PipelineJobListItem])
def list_pipeline_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> list[PipelineJobListItem]:
    rows = (
        db.query(PipelineJob, SequencingSample)
        .join(SequencingSample, PipelineJob.sample_id == SequencingSample.id)
        .order_by(
            case((PipelineJob.priority == "urgent", 0), else_=1),
            PipelineJob.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        PipelineJobListItem(
            id=job.id,
            sample_id=job.sample_id,
            paired_sample_id=job.paired_sample_id,
            module=job.module,
            stage=job.stage,
            status=job.status,
            priority=job.priority,
            backend=job.backend,
            external_job_id=job.external_job_id,
            celery_queue=job.celery_queue,
            qc_metrics=job.qc_metrics,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            sample_label=sample.sample_id,
            progress=compute_job_progress(job),
        )
        for job, sample in rows
    ]


@router.post("/run", response_model=PipelineJobResponse, status_code=202)
def start_pipeline(
    data: PipelineJobCreate,
    sync: bool = Query(False, description="اجرای همزمان بدون Celery"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_RUN)),
) -> PipelineJobResponse:
    service = PipelineService(db)
    try:
        job = service.start_pipeline(
            data.sample_id,
            async_mode=not sync,
            priority=data.priority,
            backend=data.backend,
            module=data.module,
            paired_sample_id=data.paired_sample_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PipelineJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=PipelineJobResponse)
def get_pipeline_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> PipelineJobResponse:
    service = PipelineService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    return PipelineJobResponse.model_validate(job)
