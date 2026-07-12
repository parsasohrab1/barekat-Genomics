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

    # ML Models
    model_path: str = "/data/models"
    variant_classifier_model: str = "variant_classifier_v1.pkl"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
