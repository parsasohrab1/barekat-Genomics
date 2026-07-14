"""تست ممیزی HIPAA و اسکمای گزارش."""

from barekat_genomics.core.audit import log_audit_event
from barekat_genomics.core.config import get_settings
from barekat_genomics.models.audit import AuditLog
from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.report_builder import (
    CLINICAL_REPORT_SCHEMA_VERSION,
    build_clinical_report,
    validate_clinical_content,
)
from barekat_genomics.pipeline.variant_calling import call_variants
from barekat_genomics.schemas import ClinicalReportContent


class TestAuditFlag:
    def test_log_audit_respects_enabled_flag(self, db_session, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_ENABLED", "false")
        get_settings.cache_clear()
        try:
            log_audit_event(
                db_session,
                user_id="u1",
                action="noop",
                resource_type="test",
            )
            count = db_session.query(AuditLog).filter(AuditLog.action == "noop").count()
            assert count == 0
        finally:
            monkeypatch.setenv("AUDIT_LOG_ENABLED", "true")
            get_settings.cache_clear()

    def test_log_audit_writes_when_enabled(self, db_session):
        get_settings.cache_clear()
        log_audit_event(
            db_session,
            user_id="u1",
            action="unit_test_event",
            resource_type="test",
            resource_id="r1",
        )
        row = db_session.query(AuditLog).filter(AuditLog.action == "unit_test_event").first()
        assert row is not None
        assert row.resource_id == "r1"


class TestClinicalSchemaV1:
    def test_schema_version_present(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        drugs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drugs, patient_external_id="P-SCHEMA")
        assert content["schema_version"] == CLINICAL_REPORT_SCHEMA_VERSION
        assert content["metadata"]["genome_build"] == "GRCh38"
        validated = ClinicalReportContent.model_validate(content)
        assert validated.schema_version == "1.0"

    def test_validate_upgrades_legacy_payload(self):
        legacy = {
            "executive_summary": ["خلاصه"],
            "high_priority_variants": [],
            "drug_recommendations": [],
            "drug_interactions": [],
            "digital_signature": None,
        }
        normalized = validate_clinical_content(legacy)
        assert normalized["schema_version"] == "1.0"
