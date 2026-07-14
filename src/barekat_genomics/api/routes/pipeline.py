"""Pipeline processing endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.audit import client_ip, log_audit_event
from barekat_genomics.core.config import get_settings
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.modules.registry import list_modules
from barekat_genomics.pipeline.mode import missing_production_tools
from barekat_genomics.pipeline.reference import validate_reference_bundle
from barekat_genomics.schemas import (
    ModuleInfo,
    PipelineBenchmarkMetrics,
    PipelineJobCreate,
    PipelineJobListItem,
    PipelineJobResponse,
    QcMetricsResponse,
    ReferenceValidationResponse,
)
from barekat_genomics.services.pipeline_service import PipelineService, compute_job_progress
from barekat_genomics.pipeline.validation import evaluate_simulated_benchmark

router = APIRouter(prefix="/pipeline")


def _job_response(job: PipelineJob, *, sample_label: str | None = None) -> PipelineJobResponse | PipelineJobListItem:
    data = {
        "id": job.id,
        "sample_id": job.sample_id,
        "paired_sample_id": job.paired_sample_id,
        "module": job.module,
        "stage": job.stage,
        "status": job.status,
        "priority": job.priority,
        "backend": job.backend,
        "external_job_id": job.external_job_id,
        "celery_queue": job.celery_queue,
        "qc_metrics": job.qc_metrics,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "progress": compute_job_progress(job),
        "retry_count": 0,
    }
    if sample_label is not None:
        return PipelineJobListItem(**data, sample_label=sample_label)
    return PipelineJobResponse(**data)


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


@router.get("/reference/status", response_model=ReferenceValidationResponse)
def reference_status(
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> ReferenceValidationResponse:
    settings = get_settings()
    validation = validate_reference_bundle()
    payload = validation.to_dict()
    return ReferenceValidationResponse(
        genome_build=payload["genome_build"],
        genome_version=payload["genome_version"],
        ready=payload["ready"],
        overall=payload["overall"],
        reference_dir=payload["reference_dir"],
        minio_bucket=payload["minio_bucket"],
        minio_prefix=payload["minio_prefix"],
        manifest_path=payload.get("manifest_path"),
        checks=payload["checks"],
        failed=payload.get("failed") or [],
        warnings=payload.get("warnings") or [],
        production_mode=settings.pipeline_mode == "production",
        missing_tools=missing_production_tools() if settings.pipeline_mode == "production" else [],
    )


@router.get("/benchmark/metrics", response_model=PipelineBenchmarkMetrics)
def pipeline_benchmark_metrics(
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> PipelineBenchmarkMetrics:
    """حساسیت/ویژگی اولیه روی ground truth شبیه‌سازی‌شده."""
    metrics = evaluate_simulated_benchmark()
    return PipelineBenchmarkMetrics(**metrics)


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
    return [_job_response(job, sample_label=sample.sample_id) for job, sample in rows]  # type: ignore[misc]


@router.post("/run", response_model=PipelineJobResponse, status_code=202)
def start_pipeline(
    data: PipelineJobCreate,
    request: Request,
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
    log_audit_event(
        db,
        user_id=str(user.id),
        action="run_pipeline",
        resource_type="pipeline_job",
        resource_id=str(job.id),
        details=f"sample_id={data.sample_id};sync={sync};status={job.status}",
        ip_address=client_ip(request),
    )
    return _job_response(job)  # type: ignore[return-value]


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
    return _job_response(job)  # type: ignore[return-value]


@router.get("/jobs/{job_id}/qc", response_model=QcMetricsResponse)
def get_job_qc(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PIPELINE_READ)),
) -> QcMetricsResponse:
    job = PipelineService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    qc = job.qc_metrics or {}
    return QcMetricsResponse(
        sample_id=job.sample_id,
        job_id=job.id,
        total_reads=qc.get("total_reads"),
        mean_quality=qc.get("mean_quality"),
        gc_content=qc.get("gc_content"),
        duplication_rate=qc.get("duplication_rate"),
        mean_depth=qc.get("mean_depth"),
        coverage_pct_10x=qc.get("coverage_pct_10x"),
        coverage_pct_20x=qc.get("coverage_pct_20x"),
        passed=qc.get("passed"),
        warnings=qc.get("warnings") or [],
        status=job.status,
    )
