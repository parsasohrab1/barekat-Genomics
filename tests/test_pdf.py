"""Tests for PDF generation."""

import pytest

from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.report_builder import build_clinical_report
from barekat_genomics.pipeline.variant_calling import call_variants
from barekat_genomics.services.pdf_service import _find_font, compute_report_signature, generate_clinical_pdf
from datetime import datetime, timezone


class TestPDFService:
    def test_compute_signature_deterministic(self):
        content = {"executive_summary": ["test"]}
        sig1 = compute_report_signature("report-id", content, "user-1")
        sig2 = compute_report_signature("report-id", content, "user-1")
        assert sig1 == sig2
        assert len(sig1) == 64

    @pytest.mark.skipif(_find_font() is None, reason="No Persian font available")
    def test_generate_pdf_bytes(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        drug_recs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drug_recs, patient_external_id="P-TEST")

        pdf = generate_clinical_pdf(
            report_id="00000000-0000-0000-0000-000000000099",
            patient_external_id="P-TEST",
            clinical_content=content,
            report_status="pending_review",
            created_at=datetime.now(timezone.utc),
            approved_at=None,
            approver_name=None,
            digital_signature=None,
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000
