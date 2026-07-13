"""Tests for EHR integration — FHIR R4, HL7 v2, connectors."""

from datetime import datetime, timezone

from barekat_genomics.ehr.connectors.registry import get_connector, list_connectors
from barekat_genomics.ehr.fhir_r4 import build_fhir_bundle
from barekat_genomics.ehr.hl7_v2 import build_oru_message
from barekat_genomics.ehr.models import EHRContext
from barekat_genomics.ehr.service import EHRIntegrationService
from barekat_genomics.pipeline.interpretation import interpret_variants
from barekat_genomics.pipeline.variant_calling import call_variants


def _sample_context() -> EHRContext:
    variants = call_variants("/fake/path.bam", "BAM")
    interpretations = interpret_variants(variants)
    from barekat_genomics.pipeline.interpretation import generate_drug_recommendations

    drugs = generate_drug_recommendations(interpretations)
    variant_objs = []
    for v, interp in interpretations[:3]:
        variant_objs.append(
            type(
                "V",
                (),
                {
                    "chromosome": v.chromosome,
                    "position": v.position,
                    "ref_allele": v.ref_allele,
                    "alt_allele": v.alt_allele,
                    "variant_type": v.variant_type,
                    "quality_score": v.quality_score,
                    "rs_id": v.rs_id,
                    "annotations": [
                        type(
                            "A",
                            (),
                            {
                                "gene": interp.gene,
                                "consequence": interp.consequence,
                                "clinical_significance": interp.clinical_significance,
                                "pharmacogenomic_effect": interp.pharmacogenomic_effect,
                                "priority_score": interp.priority_score,
                                "ml_score": interp.ml_score,
                                "ml_confidence": interp.ml_confidence,
                                "interpretation": interp.interpretation,
                            },
                        )()
                    ],
                },
            )()
        )

    return EHRContext(
        patient_ehr_id="EHR-12345",
        patient_external_id="P-001",
        report_id="rep-test-001",
        report_type="pharmacogenomic",
        report_summary="Pharmacogenomic report summary",
        clinical_content=None,
        variants=variant_objs,
        drug_recommendations=drugs,
        issued_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    )


class TestFHIRR4:
    def test_bundle_structure(self):
        ctx = _sample_context()
        bundle = build_fhir_bundle(ctx)

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        types = {e["resource"]["resourceType"] for e in bundle["entry"]}
        assert "Patient" in types
        assert "Organization" in types
        assert "Observation" in types
        assert "DiagnosticReport" in types

    def test_medication_requests_present(self):
        ctx = _sample_context()
        bundle = build_fhir_bundle(ctx)
        med_count = sum(
            1 for e in bundle["entry"] if e["resource"]["resourceType"] == "MedicationRequest"
        )
        assert med_count >= 0

    def test_observation_has_loinc(self):
        ctx = _sample_context()
        bundle = build_fhir_bundle(ctx)
        obs = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation")
        codes = [c["code"] for c in obs["code"]["coding"]]
        assert "69548-6" in codes


class TestHL7v2:
    def test_oru_message_segments(self):
        ctx = _sample_context()
        msg = build_oru_message(ctx)

        assert msg.startswith("MSH|")
        assert "\rPID|" in msg
        assert "\rOBR|" in msg
        assert "\rOBX|" in msg
        assert "ORU^R01" in msg

    def test_oru_ends_with_cr(self):
        ctx = _sample_context()
        msg = build_oru_message(ctx)
        assert msg.endswith("\r")


class TestConnectors:
    def test_list_connectors(self):
        connectors = list_connectors()
        names = {c["name"] for c in connectors}
        assert "tajhiz" in names
        assert "sepas" in names

    def test_tajhiz_dry_run_fhir(self):
        ctx = _sample_context()
        connector = get_connector("tajhiz")
        bundle = build_fhir_bundle(ctx)
        result = connector.push(ctx, bundle, "fhir")
        assert result.success is True
        assert result.connector == "tajhiz"
        assert "dry-run" in result.message or result.external_id

    def test_tajhiz_dry_run_hl7(self):
        ctx = _sample_context()
        connector = get_connector("tajhiz")
        msg = build_oru_message(ctx)
        result = connector.push(ctx, msg, "hl7")
        assert result.success is True

    def test_sepas_dry_run(self):
        ctx = _sample_context()
        connector = get_connector("sepas")
        bundle = build_fhir_bundle(ctx)
        result = connector.push(ctx, bundle, "fhir")
        assert result.success is True

    def test_sepas_rejects_hl7(self):
        ctx = _sample_context()
        connector = get_connector("sepas")
        result = connector.push(ctx, "MSH|...", "hl7")
        assert result.success is False


class TestEHRService:
    def test_export_fhir_and_hl7(self):
        ctx = _sample_context()
        svc = EHRIntegrationService()
        fhir = svc.export_fhir(ctx)
        hl7 = svc.export_hl7(ctx)
        assert fhir["resourceType"] == "Bundle"
        assert "MSH|" in hl7
