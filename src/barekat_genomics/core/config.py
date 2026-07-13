"""تنظیمات مرکزی پلتفرم."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "barekat-genomics"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    auth_enabled: bool = True
    access_token_expire_minutes: int = 480

    # Database
    database_url: str = "postgresql://barekat:barekat@localhost:5432/barekat_genomics"

    # Redis & Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Object Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "barekat"
    s3_secret_key: str = "barekatsecret"
    s3_bucket: str = "barekat-genomics"
    s3_region: str = "us-east-1"

    # HIPAA / Security
    encryption_key: str = "change-me-32-byte-key-for-phi!!"
    audit_log_enabled: bool = True
    phi_retention_days: int = 2555  # ~7 years per HIPAA

    # Reference Databases
    dbsnp_path: str = "/data/reference/dbsnp"
    genome_build: str = "GRCh38"
    reference_dir: str = "/data/reference/GRCh38"
    ref_fasta: str = ""
    bwa_index_prefix: str = ""
    snpeff_db: str = "GRCh38.99"
    clinvar_path: str = "/data/reference/clinvar/clinvar.vcf.gz"
    pharmgkb_path: str = "/data/reference/pharmgkb"
    knowledge_dir: str = ""
    gnomad_path: str = ""
    ml_ab_test_enabled: bool = False
    ml_ab_test_challenger: str = "v2"
    ml_ab_test_traffic_pct: float = 0.1

    # Pipeline
    pipeline_mode: Literal["simulated", "production"] = "simulated"
    pipeline_work_dir: str = "/data/processed"
    pipeline_backend: Literal["celery", "nextflow", "kubernetes", "aws_batch"] = "celery"
    pipeline_workflow_engine: Literal["nextflow", "snakemake", "native"] = "native"

    # Nextflow
    nextflow_executable: str = "nextflow"
    nextflow_workflow_path: str = "workflows/nextflow/main.nf"
    nextflow_profile: str = "standard"
    nextflow_executor: str = ""  # local, k8s, awsbatch

    # Kubernetes
    kubernetes_namespace: str = "barekat"
    kubernetes_job_template: str = "k8s/pipeline-job.yaml"
    kubernetes_worker_image: str = "barekat-genomics-worker:latest"

    # AWS Batch
    aws_region: str = "eu-central-1"
    aws_batch_job_queue: str = ""
    aws_batch_job_definition: str = ""

    # Annotation cache
    annotation_cache_enabled: bool = True
    annotation_cache_ttl_seconds: int = 604800

    # ML Models
    model_path: str = "/data/models"
    variant_classifier_model: str = "variant_classifier_v1.pkl"

    # EHR Integration
    ehr_fhir_organization_id: str = "barekat-genomics"
    ehr_hl7_sending_facility: str = "BAREKAT"
    ehr_hl7_receiving_facility: str = "HIS"
    ehr_connector_timeout: int = 30
    tajhiz_api_url: str = ""
    tajhiz_api_key: str = ""
    sepas_api_url: str = ""
    sepas_api_key: str = ""

    # AI decision support (no direct diagnosis)
    ai_assist_enabled: bool = True

    # Observability
    metrics_enabled: bool = True
    log_json: bool = False
    log_level: str = "INFO"
    sentry_dsn: str = ""
    sentry_release: str = ""
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.0

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
