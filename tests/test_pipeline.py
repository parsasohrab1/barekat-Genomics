"""Tests for barekat-genomics."""

import pytest

from barekat_genomics.pipeline.preprocessing import run_quality_control
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants, filter_variants
from barekat_genomics.pipeline.interpretation import interpret_variants
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.pipeline.mode import is_production_pipeline
from barekat_genomics.ml.classifier import VariantClassifier


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "version" in data


class TestPipeline:
    def test_quality_control_fastq(self):
        qc = run_quality_control("/fake/path.fastq", "FASTQ")
        assert qc.passed is True
        assert qc.total_reads > 0

    def test_quality_control_bam(self):
        qc = run_quality_control("/fake/path.bam", "BAM")
        assert qc.passed is True

    def test_variant_calling(self):
        variants = call_variants("/fake/path.bam", "BAM")
        assert len(variants) > 0
        filtered = filter_variants(variants)
        assert len(filtered) <= len(variants)

    def test_variant_interpretation(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        assert len(interpretations) == len(variants)
        for _, interp in interpretations:
            assert interp.clinical_significance is not None
            assert 0 <= interp.priority_score <= 1
            assert 0 <= interp.ml_score <= 1

    def test_full_pipeline(self):
        result = run_full_pipeline("/fake/path.bam", "BAM")
        assert result.success is True
        assert len(result.variants) > 0
        assert result.report_summary is not None


class TestMLClassifier:
    def test_predict(self):
        from barekat_genomics.knowledge.models import VariantKnowledge
        from barekat_genomics.ml.features import extract_features

        classifier = VariantClassifier()
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 95.0, 40.0, "rs4244285")
        kb = VariantKnowledge(gene="CYP2C19", cadd_phred=18.0, sift_score=0.01, polyphen_score=0.9)
        fv = extract_features(v, "CYP2C19", kb)
        score, confidence, _ = classifier.predict(fv)
        assert 0 <= score <= 1
        assert 0 <= confidence <= 1


class TestPipelineMode:
    def test_simulated_mode_in_tests(self):
        assert is_production_pipeline() is False
