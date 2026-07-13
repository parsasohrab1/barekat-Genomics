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
    priority: str = Field("normal", pattern="^(normal|urgent)$")


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    sample_id: str
    file_type: str
    status: str
    priority: str = "normal"
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

    id: UUID | None = None
    gene: str | None
    consequence: str | None
    clinical_significance: str | None
    pharmacogenomic_effect: str | None
    priority_score: float | None
    ml_score: float | None = None
    ml_confidence: float | None
    interpretation: str | None
    requires_genetic_review: bool | None = None
    review_status: str | None = None
    review_notes: str | None = None


class VariantWithAnnotation(VariantResponse):
    annotations: list[VariantAnnotationResponse] = []


# --- Pipeline ---
MODULE_IDS = (
    "pharmacogenomics|pgx_panel|cgp|carrier_screening|tumor_normal|prs"
)


class PipelineJobCreate(BaseModel):
    sample_id: UUID
    priority: str | None = Field(None, pattern="^(normal|urgent)$")
    backend: str | None = Field(None, pattern="^(celery|nextflow|kubernetes|aws_batch)$")
    module: str | None = Field(None, pattern=f"^({MODULE_IDS})$")
    paired_sample_id: UUID | None = None


class ModuleInfo(BaseModel):
    id: str
    name_fa: str
    name_en: str
    description_fa: str
    category: str
    gene_count: int
    requires_paired_sample: bool = False
    cpic_guideline: bool = False


class PipelineJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_id: UUID
    paired_sample_id: UUID | None = None
    module: str = "pharmacogenomics"
    stage: str
    status: str
    priority: str = "normal"
    backend: str = "celery"
    external_job_id: str | None = None
    celery_queue: str | None = None
    qc_metrics: dict | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# --- Report ---
class HighPriorityVariant(BaseModel):
    gene: str | None = None
    rs_id: str | None = None
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    clinical_significance: str
    priority_score: float
    interpretation: str | None = None
    pharmacogenomic_effect: str | None = None


class ClinicalDrugRecommendation(BaseModel):
    drug: str
    drug_fa: str | None = None
    gene: str | None = None
    significance: str | None = None
    recommendation: str | None = None
    confidence: float | None = None
    cpic_level: str | None = None
    cpic_level_label: str | None = None
    cpic_guideline: str | None = None
    action_fa: str | None = None


class DrugInteractionWarning(BaseModel):
    drugs: list[str]
    drugs_fa: list[str] | None = None
    severity: str
    severity_label: str | None = None
    warning_fa: str
    recommendation_fa: str


class DigitalSignature(BaseModel):
    signature: str
    signed_at: str | None = None
    approver_id: str | None = None


class ClinicalReportContent(BaseModel):
    executive_summary: list[str] = []
    high_priority_variants: list[HighPriorityVariant] = []
    drug_recommendations: list[ClinicalDrugRecommendation] = []
    drug_interactions: list[DrugInteractionWarning] = []
    digital_signature: DigitalSignature | dict | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    report_type: str
    status: str
    summary: str | None
    drug_recommendations: dict | None
    clinical_content: ClinicalReportContent | dict | None = None
    variant_summary: dict | None
    created_at: datetime
    finalized_at: datetime | None
    approved_at: datetime | None = None


# --- EHR Integration ---
class EHRVariantExport(BaseModel):
    patient_ehr_id: str
    report_id: UUID | None = None
    issued_at: datetime | None = None
    variants: list[VariantWithAnnotation]
    drug_recommendations: dict | None
    report_summary: str | None
    clinical_content: dict | None = None


class EHRConnectorInfo(BaseModel):
    name: str
    display_name: str
    display_name_fa: str
    supported_formats: list[str]


class EHRPushRequest(BaseModel):
    connector: str = Field(..., pattern="^(tajhiz|sepas)$")
    format: str = Field("fhir", pattern="^(fhir|hl7|json)$")


class EHRPushResponse(BaseModel):
    success: bool
    connector: str
    format: str
    message: str
    external_id: str | None = None
    details: dict | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


# --- Auth ---
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    created_at: datetime


class ReportApproveRequest(BaseModel):
    clinician_notes: str | None = None


class VariantReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(approved|rejected)$")
    notes: str | None = None


class PendingVariantItem(BaseModel):
    annotation_id: UUID
    variant: VariantResponse
    gene: str | None = None
    ml_score: float | None = None
    ml_confidence: float | None = None
    clinical_significance: str | None = None
    interpretation: str | None = None
    review_status: str | None = None
    pharmacogenomic_effect: str | None = None


class ReviewQueueItem(ReportResponse):
    pending_variant_count: int = 0


class DashboardStatsResponse(BaseModel):
    total_patients: int
    total_samples: int
    active_pipelines: int
    completed_reports: int
    variants_detected: int
    drug_recommendations: int


class SampleListItem(SampleResponse):
    patient_external_id: str | None = None


class PipelineJobListItem(PipelineJobResponse):
    sample_label: str | None = None
    progress: int = 0


# --- AI Decision Support ---
class PlainSummaryResponse(BaseModel):
    report_id: str | None = None
    plain_summary: list[str]
    plain_summary_text: str
    disclaimer: str
    decision_support_only: bool = True
    source: str = "rule_based"


class VariantAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    variant_id: UUID | None = None
    rs_id: str | None = Field(None, pattern=r"^rs?\d+$")


class VariantAskResponse(BaseModel):
    answer_fa: str
    blocked: bool = False
    disclaimer: str
    decision_support_only: bool = True
    sources: list[str] = []
    context_chunks: list[str] = []
    question: str | None = None
    variant_id: str | None = None
    rs_id: str | None = None


class VariantListItem(VariantWithAnnotation):
    patient_external_id: str | None = None
    drug: str | None = None
