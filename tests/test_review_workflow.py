"""Tests for geneticist review workflow."""

from barekat_genomics.core.review import ML_REVIEW_THRESHOLD, VARIANT_REVIEW_REJECTED
from barekat_genomics.pipeline.interpretation import VariantInterpretation
from barekat_genomics.pipeline.report_builder import build_clinical_report
from barekat_genomics.pipeline.variant_calling import CalledVariant


class TestGeneticReviewWorkflow:
    def test_ml_review_threshold(self):
        assert ML_REVIEW_THRESHOLD == 0.7

    def test_rejected_variants_excluded_from_clinical_report(self):
        variant = CalledVariant("chr10", 96521657, "C", "T", "SNP", 95.0, 40.0, "rs4244285")
        interp = VariantInterpretation(
            gene="CYP2C19",
            consequence="missense_variant",
            clinical_significance="pathogenic",
            pharmacogenomic_effect="Reduced metabolism",
            priority_score=0.85,
            ml_confidence=0.9,
            ml_score=0.82,
            interpretation="High-risk PGx variant",
            knowledge_sources=["pharmgkb"],
        )
        content = build_clinical_report(
            [(variant, interp)],
            {},
            review_status_by_key={"rs4244285": VARIANT_REVIEW_REJECTED},
        )
        assert content["high_priority_variants"] == []

    def test_approved_high_ml_variants_included(self):
        variant = CalledVariant("chr10", 96521657, "C", "T", "SNP", 95.0, 40.0, "rs4244285")
        interp = VariantInterpretation(
            gene="CYP2C19",
            consequence="missense_variant",
            clinical_significance="pathogenic",
            pharmacogenomic_effect="Reduced metabolism",
            priority_score=0.85,
            ml_confidence=0.9,
            ml_score=0.82,
            interpretation="High-risk PGx variant",
            knowledge_sources=["pharmgkb"],
        )
        content = build_clinical_report([(variant, interp)], {})
        assert len(content["high_priority_variants"]) == 1
        assert content["high_priority_variants"][0]["gene"] == "CYP2C19"

    def test_low_ml_score_not_high_priority(self):
        variant = CalledVariant("chr1", 100, "A", "G", "SNP", 80.0, 30.0, "rs123")
        interp = VariantInterpretation(
            gene="GENE1",
            consequence="synonymous",
            clinical_significance="benign",
            pharmacogenomic_effect=None,
            priority_score=0.6,
            ml_confidence=0.5,
            ml_score=0.4,
            interpretation="Low risk",
            knowledge_sources=[],
        )
        content = build_clinical_report([(variant, interp)], {})
        assert content["high_priority_variants"] == []
