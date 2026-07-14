"""API عمومی شرکای آزمایشگاهی (X-API-Key)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.middleware.rate_limit import check_partner_rate
from barekat_genomics.core.audit import client_ip, log_audit_event
from barekat_genomics.core.database import get_db
from barekat_genomics.pipeline.assay_config import ASSAY_TYPES, FILE_TYPES
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.schemas import PatientCreate, PatientResponse
from barekat_genomics.services.api_key_service import ApiKeyService
from barekat_genomics.services.patient_service import PatientService
from barekat_genomics.services.result_cache_service import (
    ComputeCostService,
    ResultCacheService,
    build_pipeline_cache_key,
    content_hash_for_path,
)

router = APIRouter(prefix="/partner")


class PartnerContext(BaseModel):
    organization_id: uuid.UUID
    key_id: uuid.UUID
    scopes: list[str]
    rate_limit_per_minute: int


def get_partner(
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> PartnerContext:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key لازم است")
    row = ApiKeyService(db).authenticate(x_api_key)
    if not row:
        raise HTTPException(status_code=401, detail="کلید API نامعتبر")
    check_partner_rate(str(row.id), row.rate_limit_per_minute or 60)
    return PartnerContext(
        organization_id=row.organization_id,
        key_id=row.id,
        scopes=[s.strip() for s in (row.scopes or "").split(",") if s.strip()],
        rate_limit_per_minute=row.rate_limit_per_minute,
    )


def _require_scope(partner: PartnerContext, scope: str) -> None:
    if "*" in partner.scopes or scope in partner.scopes:
        return
    raise HTTPException(status_code=403, detail=f"scope لازم است: {scope}")


class PartnerPatientIn(BaseModel):
    external_id: str
    name: str | None = None
    age: int | None = None
    gender: str | None = None


class PartnerPipelineIn(BaseModel):
    file_path: str = Field(description="مسیر محلی یا آبجکت ذخیره‌شده")
    file_type: str = Field(pattern="^(FASTQ|BAM|VCF|CRAM)$")
    assay_type: str = Field(default="panel", pattern="^(wgs|wes|panel)$")
    genome_build: str = "GRCh38"
    sample_label: str | None = None
    module_id: str = "pharmacogenomics"
    use_cache: bool = True


@router.get("/health")
def partner_health(partner: PartnerContext = Depends(get_partner)) -> dict:
    return {
        "status": "ok",
        "organization_id": str(partner.organization_id),
        "scopes": partner.scopes,
        "supported_file_types": list(FILE_TYPES),
        "supported_assays": list(ASSAY_TYPES),
    }


@router.post("/patients", response_model=PatientResponse, status_code=201)
def partner_create_patient(
    body: PartnerPatientIn,
    request: Request,
    db: Session = Depends(get_db),
    partner: PartnerContext = Depends(get_partner),
) -> PatientResponse:
    _require_scope(partner, "samples:write")
    patient = PatientService(db).create(
        PatientCreate(
            external_id=body.external_id,
            name=body.name,
            age=body.age,
            gender=body.gender,
        ),
        organization_id=partner.organization_id,
    )
    log_audit_event(
        db,
        user_id=f"api_key:{partner.key_id}",
        action="partner_create_patient",
        resource_type="patient",
        resource_id=str(patient.id),
        ip_address=client_ip(request),
    )
    return PatientResponse.model_validate(patient)


@router.post("/pipeline/run")
def partner_run_pipeline(
    body: PartnerPipelineIn,
    request: Request,
    db: Session = Depends(get_db),
    partner: PartnerContext = Depends(get_partner),
) -> dict:
    _require_scope(partner, "pipeline:run")
    chash = content_hash_for_path(body.file_path)
    cache_key = build_pipeline_cache_key(
        content_hash=chash,
        file_type=body.file_type,
        assay_type=body.assay_type,
        genome_build=body.genome_build,
        module_id=body.module_id,
    )
    cache_svc = ResultCacheService(db)
    cost_svc = ComputeCostService(db)

    if body.use_cache:
        cached = cache_svc.get(cache_key)
        if cached:
            cost_svc.record(
                organization_id=partner.organization_id,
                job_id=None,
                assay_type=body.assay_type,
                backend="partner_api",
                cache_hit=True,
                notes="partner cache hit",
            )
            return {"cache_hit": True, "result": cached, "estimate": cost_svc.estimate(body.assay_type, cache_hit=True)}

    result = run_full_pipeline(
        body.file_path,
        body.file_type,
        body.genome_build,
        sample_label=body.sample_label,
        module_id=body.module_id,
        assay_type=body.assay_type,
    )
    payload = {
        "success": result.success,
        "report_summary": result.report_summary,
        "error": result.error,
        "qc_metrics": result.qc_metrics.to_dict() if result.qc_metrics else None,
        "n_variants": len(result.variants),
        "clinical_content": result.clinical_content,
        "assay_type": body.assay_type,
    }
    if result.success and body.use_cache:
        cache_svc.put(
            cache_key=cache_key,
            content_hash=chash,
            file_type=body.file_type,
            assay_type=body.assay_type,
            genome_build=body.genome_build,
            module_id=body.module_id,
            result=payload,
        )
    cost_svc.record(
        organization_id=partner.organization_id,
        job_id=None,
        assay_type=body.assay_type,
        backend="partner_api",
        cache_hit=False,
    )
    log_audit_event(
        db,
        user_id=f"api_key:{partner.key_id}",
        action="partner_pipeline_run",
        resource_type="pipeline",
        resource_id=None,
        details=f"assay={body.assay_type};file_type={body.file_type};success={result.success}",
        ip_address=client_ip(request),
    )
    return {"cache_hit": False, "result": payload, "estimate": cost_svc.estimate(body.assay_type)}
