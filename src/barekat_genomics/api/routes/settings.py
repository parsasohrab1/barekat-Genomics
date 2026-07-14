"""تنظیمات پلتفرم و وضعیت HIPAA (فقط خواندنی از env)."""

from fastapi import APIRouter, Depends

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.config import get_settings
from barekat_genomics.core.rbac import Permission
from barekat_genomics.pipeline.report_builder import CLINICAL_REPORT_SCHEMA_VERSION
from barekat_genomics.schemas import PlatformSettingsResponse

router = APIRouter(prefix="/settings")


@router.get("/", response_model=PlatformSettingsResponse)
def get_platform_settings(
    user: CurrentUser = Depends(require_permission(Permission.ADMIN_SETTINGS)),
) -> PlatformSettingsResponse:
    settings = get_settings()
    return PlatformSettingsResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        auth_enabled=settings.auth_enabled,
        audit_log_enabled=settings.audit_log_enabled,
        phi_retention_days=settings.phi_retention_days,
        genome_build=settings.genome_build,
        pipeline_mode=settings.pipeline_mode,
        pipeline_backend=settings.pipeline_backend,
        ai_assist_enabled=settings.ai_assist_enabled,
        metrics_enabled=settings.metrics_enabled,
        ml_ab_test_enabled=settings.ml_ab_test_enabled,
        variant_classifier_model=settings.variant_classifier_model,
        ehr_fhir_organization_id=settings.ehr_fhir_organization_id,
        ehr_hl7_sending_facility=settings.ehr_hl7_sending_facility,
        clinical_report_schema_version=CLINICAL_REPORT_SCHEMA_VERSION,
    )
