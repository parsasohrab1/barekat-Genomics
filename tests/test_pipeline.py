"""Tests for barekat-genomics."""

import pytest
from fastapi.testclient import TestClient

from barekat_genomics.api.main import create_app
from barekat_genomics.pipeline.preprocessing import run_quality_control
from barekat_genomics.pipeline.variant_calling import call_variants, filter_variants
from barekat_genomics.pipeline.interpretation import interpret_variants
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.ml.classifier import VariantClassifier


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
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

    def test_full_pipeline(self):
        result = run_full_pipeline("/fake/path.bam", "BAM")
        assert result.success is True
        assert len(result.variants) > 0
        assert result.report_summary is not None


class TestMLClassifier:
    def test_predict(self):
        classifier = VariantClassifier()
        score, confidence = classifier.predict([95.0, 40.0, 1.0, 1.0, 1.0])
        assert 0 <= score <= 1
        assert 0 <= confidence <= 1
