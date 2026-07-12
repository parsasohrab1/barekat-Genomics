"""Pydantic schemas برای API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Patient ---
class PatientCreate(BaseModel):
    external_id: str
    name: str | None = None
    age: int | None = Field(None, ge=0, le=150)
    gender: str | None = None
    clinical_notes: str | None = None
    ehr_patient_id: str | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    age: int | None
    gender: str | None
    ehr_patient_id: str | None
    created_at: datetime


# --- Sample ---
class SampleCreate(BaseModel):
    patient_id: UUID
    sample_id: str
    file_type: str = Field(..., pattern="^(FASTQ|BAM)$")


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    sample_id: str
    file_type: str
    status: str
    genome_build: str
    created_at: datetime


# --- Variant ---
class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    variant_type: str
    quality_score: float | None
    rs_id: str | None


class VariantAnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gene: str | None
    consequence: str | None
    clinical_significance: str | None
    pharmacogenomic_effect: str | None
    priority_score: float | None
    ml_confidence: float | None
    interpretation: str | None


class VariantWithAnnotation(VariantResponse):
    annotations: list[VariantAnnotationResponse] = []


# --- Pipeline ---
class PipelineJobCreate(BaseModel):
    sample_id: UUID


class PipelineJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_id: UUID
    stage: str
    status: str
    qc_metrics: dict | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# --- Report ---
class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    report_type: str
    status: str
    summary: str | None
    drug_recommendations: dict | None
    variant_summary: dict | None
    created_at: datetime
    finalized_at: datetime | None


# --- EHR Integration ---
class EHRVariantExport(BaseModel):
    patient_ehr_id: str
    variants: list[VariantWithAnnotation]
    drug_recommendations: dict | None
    report_summary: str | None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
