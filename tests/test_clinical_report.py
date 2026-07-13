"""Tests for clinical report builder and CPIC."""

from barekat_genomics.pipeline.cpic import detect_drug_interactions
from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.report_builder import build_clinical_report, executive_summary_text
from barekat_genomics.pipeline.variant_calling import call_variants


class TestClinicalReport:
    def test_build_clinical_report_structure(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        drug_recs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drug_recs, patient_external_id="P-001")

        assert 3 <= len(content["executive_summary"]) <= 5
        assert isinstance(content["high_priority_variants"], list)
        assert isinstance(content["drug_recommendations"], list)
        assert isinstance(content["drug_interactions"], list)
        assert content["digital_signature"] is None

        summary_text = executive_summary_text(content)
        assert "P-001" in summary_text
        assert len(summary_text) > 50

    def test_drug_recommendations_have_cpic_level(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        drug_recs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drug_recs)

        for drug in content["drug_recommendations"]:
            assert "cpic_level" in drug
            assert "cpic_level_label" in drug
            assert "action_fa" in drug

    def test_detect_warfarin_clopidogrel_interaction(self):
        interactions = detect_drug_interactions(["warfarin", "clopidogrel"])
        assert len(interactions) == 1
        assert interactions[0]["severity"] == "major"

    def test_high_priority_variants_threshold(self):
        from barekat_genomics.core.review import ML_REVIEW_THRESHOLD

        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        drug_recs = generate_drug_recommendations(interpretations)
        content = build_clinical_report(interpretations, drug_recs)

        hp_genes = {v["gene"] for v in content["high_priority_variants"] if v.get("gene")}
        for _, interp in interpretations:
            if interp.gene and interp.gene in hp_genes:
                assert interp.ml_score > ML_REVIEW_THRESHOLD
            if interp.ml_score > ML_REVIEW_THRESHOLD and interp.gene:
                assert interp.gene in hp_genes
