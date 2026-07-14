"""Sequencing sample endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, assert_patient_access, require_permission
from barekat_genomics.core.audit import client_ip, log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, is_physician_role
from barekat_genomics.core.storage import get_storage
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.schemas import QcMetricsResponse, SampleListItem, SampleResponse
from barekat_genomics.services.patient_service import PatientService

router = APIRouter(prefix="/samples")


@router.get("/", response_model=list[SampleListItem])
def list_samples(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.SAMPLES_READ)),
) -> list[SampleListItem]:
    from barekat_genomics.models.patient import Patient

    rows = (
        db.query(SequencingSample, Patient)
        .join(Patient, SequencingSample.patient_id == Patient.id)
        .order_by(SequencingSample.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    if user.organization_id is not None:
        rows = [(s, p) for s, p in rows if p.organization_id == user.organization_id]
    if is_physician_role(user.role):
        rows = [(s, p) for s, p in rows if p.assigned_clinician_id == user.id]

    return [
        SampleListItem(
            id=sample.id,
            patient_id=sample.patient_id,
            sample_id=sample.sample_id,
            file_type=sample.file_type,
            assay_type=getattr(sample, "assay_type", None) or "panel",
            target_bed=getattr(sample, "target_bed", None),
            status=sample.status,
            priority=sample.priority,
            genome_build=sample.genome_build,
            created_at=sample.created_at,
            patient_external_id=patient.external_id,
        )
        for sample, patient in rows
    ]


@router.post("/upload", response_model=SampleResponse, status_code=201)
async def upload_sample(
    request: Request,
    patient_id: uuid.UUID = Form(...),
    sample_id: str = Form(...),
    file_type: str = Form(...),
    assay_type: str = Form("panel"),
    priority: str = Form("normal"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.SAMPLES_WRITE)),
) -> SampleResponse:
    if file_type not in ("FASTQ", "BAM", "VCF", "CRAM"):
        raise HTTPException(status_code=400, detail="نوع فایل باید FASTQ، BAM، VCF یا CRAM باشد")
    if assay_type not in ("wgs", "wes", "panel"):
        raise HTTPException(status_code=400, detail="assay_type باید wgs، wes یا panel باشد")
    if priority not in ("normal", "urgent"):
        raise HTTPException(status_code=400, detail="اولویت باید normal یا urgent باشد")

    patient_service = PatientService(db)
    patient = patient_service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)

    storage = get_storage()
    object_key = f"samples/{patient_id}/{sample_id}/{file.filename}"
    content = await file.read()
    storage_path = storage.upload_bytes(content, object_key)

    from barekat_genomics.pipeline.assay_config import resolve_target_bed

    bed = resolve_target_bed(assay_type)
    sample = SequencingSample(
        patient_id=patient_id,
        sample_id=sample_id,
        file_type=file_type,
        assay_type=assay_type,
        target_bed=str(bed) if bed else None,
        storage_path=storage_path,
        status="uploaded",
        priority=priority,
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    log_audit_event(
        db,
        user_id=str(user.id),
        action="upload_sample",
        resource_type="sample",
        resource_id=str(sample.id),
        details=f"file_type={file_type};sample_id={sample_id}",
        ip_address=client_ip(request),
    )
    return SampleResponse.model_validate(sample)


@router.get("/{sample_id}/qc", response_model=QcMetricsResponse)
def get_sample_qc(
    sample_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.SAMPLES_READ)),
) -> QcMetricsResponse:
    from barekat_genomics.models.pipeline import PipelineJob

    sample = db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="نمونه یافت نشد")
    patient = PatientService(db).get_by_id(sample.patient_id)
    if patient:
        assert_patient_access(user, patient)

    job = (
        db.query(PipelineJob)
        .filter(PipelineJob.sample_id == sample_id)
        .order_by(PipelineJob.created_at.desc())
        .first()
    )
    qc = (job.qc_metrics if job else None) or {}
    return QcMetricsResponse(
        sample_id=sample.id,
        job_id=job.id if job else None,
        total_reads=qc.get("total_reads"),
        mean_quality=qc.get("mean_quality"),
        gc_content=qc.get("gc_content"),
        duplication_rate=qc.get("duplication_rate"),
        mean_depth=qc.get("mean_depth"),
        coverage_pct_10x=qc.get("coverage_pct_10x"),
        coverage_pct_20x=qc.get("coverage_pct_20x"),
        passed=qc.get("passed"),
        warnings=qc.get("warnings") or [],
        status=job.status if job else sample.status,
    )


@router.get("/{sample_id}", response_model=SampleResponse)
def get_sample(
    sample_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.SAMPLES_READ)),
) -> SampleResponse:
    sample = db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="نمونه یافت نشد")
    patient = PatientService(db).get_by_id(sample.patient_id)
    if patient:
        assert_patient_access(user, patient)
    return SampleResponse.model_validate(sample)
