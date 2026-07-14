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
    file_type: str = Field(..., pattern="^(FASTQ|BAM|VCF|CRAM)$")
    assay_type: str = Field("panel", pattern="^(wgs|wes|panel)$")
    priority: str = Field("normal", pattern="^(normal|urgent)$")


class SampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    sample_id: str
    file_type: str
    assay_type: str | None = "panel"
    target_bed: str | None = None
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
    progress: int = 0
    retry_count: int = 0


class ReferenceValidationResponse(BaseModel):
    genome_build: str
    genome_version: str = ""
    ready: bool
    overall: str = "FAIL"
    reference_dir: str = ""
    minio_bucket: str = ""
    minio_prefix: str = ""
    manifest_path: str | None = None
    checks: list[dict]
    failed: list[str] = []
    warnings: list[str] = []
    production_mode: bool = False
    missing_tools: list[str] = []


class QcMetricsResponse(BaseModel):
    sample_id: UUID
    job_id: UUID | None = None
    total_reads: int | None = None
    mean_quality: float | None = None
    gc_content: float | None = None
    duplication_rate: float | None = None
    mean_depth: float | None = None
    coverage_pct_10x: float | None = None
    coverage_pct_20x: float | None = None
    passed: bool | None = None
    warnings: list[str] = []
    status: str | None = None


class PipelineBenchmarkMetrics(BaseModel):
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    sensitivity: float
    specificity: float | None = None
    matched_rs_ids: list[str] = []
    missed_rs_ids: list[str] = []
    extra_rs_ids: list[str] = []
    mode: str = "simulated"
# --- Report ---
class FeatureContribution(BaseModel):
    feature: str
    contribution: float | None = None
    importance: float | None = None


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
    ml_score: float | None = None
    ml_confidence: float | None = None
    rank: int | None = None
    model_version: str | None = None
    explain_method: str | None = None
    feature_contributions: list[FeatureContribution | dict] = []
    guideline_drugs: list[str] = []
    knowledge_sources: list[str] = []


class BiomarkerMarker(BaseModel):
    rank: int | None = None
    gene: str | None = None
    rs_id: str | None = None
    clinical_significance: str | None = None
    priority_score: float | None = None
    ml_score: float | None = None
    pharmacogenomic_effect: str | None = None
    guideline_drugs: list[str] = []
    knowledge_sources: list[str] = []
    top_features: list[FeatureContribution | dict] = []
    explain_method: str | None = None
    high_priority: bool = False


class BiomarkerPanel(BaseModel):
    total_variants: int = 0
    high_priority_count: int = 0
    ranked_markers: list[BiomarkerMarker] = []


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
    sources: list[str] = []
    pgx_level: str | None = None
    clinvar_review_status: str | None = None
    variant_rank: int | None = None
    phenotype: str | None = None


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


class ClinicalReportMetadata(BaseModel):
    genome_build: str | None = None
    patient_external_id: str | None = None
    pipeline_version: str | None = None


class ClinicalReportContent(BaseModel):
    schema_version: str = "1.0"
    executive_summary: list[str] = []
    high_priority_variants: list[HighPriorityVariant] = []
    biomarker_panel: BiomarkerPanel | dict | None = None
    drug_recommendations: list[ClinicalDrugRecommendation] = []
    drug_interactions: list[DrugInteractionWarning] = []
    digital_signature: DigitalSignature | dict | None = None
    metadata: ClinicalReportMetadata | dict | None = None


class PlatformSettingsResponse(BaseModel):
    app_name: str
    app_env: str
    auth_enabled: bool
    audit_log_enabled: bool
    phi_retention_days: int
    genome_build: str
    pipeline_mode: str
    pipeline_backend: str
    ai_assist_enabled: bool
    metrics_enabled: bool
    ml_ab_test_enabled: bool
    variant_classifier_model: str
    ehr_fhir_organization_id: str
    ehr_hl7_sending_facility: str
    clinical_report_schema_version: str = "1.0"


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
    organization_id: UUID | None = None
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
