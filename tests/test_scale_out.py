"""Tests for scale-out: priority queues, annotation cache, runners."""

from dataclasses import asdict

from barekat_genomics.pipeline.interpretation import VariantInterpretation, interpret_variants
from barekat_genomics.pipeline.priority import resolve_celery_queue, resolve_priority
from barekat_genomics.pipeline.variant_calling import CalledVariant
from barekat_genomics.services.annotation_cache_service import (
    AnnotationCacheService,
    build_cache_key,
)


class TestPriorityQueues:
    def test_urgent_resolves_to_urgent_queue(self):
        assert resolve_priority("urgent") == "urgent"
        assert resolve_celery_queue("urgent") == "urgent"

    def test_normal_resolves_to_default_queue(self):
        assert resolve_priority("normal") == "normal"
        assert resolve_priority(None) == "normal"
        assert resolve_celery_queue("normal") == "default"


class TestAnnotationCache:
    def test_cache_key_uses_rsid(self):
        v = CalledVariant("chr10", 1, "A", "G", "SNP", 90.0, 30.0, "rs4244285")
        key = build_cache_key(v, genome_build="GRCh38", model_version="v1")
        assert key == "ann:GRCh38:v1:rs4244285"

    def test_cache_key_without_rsid(self):
        v = CalledVariant("chr1", 100, "A", "G", "SNP", 90.0, 30.0, None)
        key = build_cache_key(v, genome_build="GRCh38", model_version="v1")
        assert "chr1:100:A:G" in key

    def test_interp_roundtrip(self):
        interp = VariantInterpretation(
            gene="CYP2C19",
            consequence="missense",
            clinical_significance="pathogenic",
            pharmacogenomic_effect="test",
            priority_score=0.8,
            ml_confidence=0.9,
            ml_score=0.85,
            interpretation="test interp",
            knowledge_sources=["pharmgkb"],
        )
        data = asdict(interp)
        restored = VariantInterpretation(**data)
        assert restored.gene == "CYP2C19"
        assert restored.ml_score == 0.85


class TestRunners:
    def test_get_celery_runner(self):
        from barekat_genomics.pipeline.runners import get_runner

        runner = get_runner("celery")
        assert runner.name == "celery"

    def test_unknown_runner_raises(self):
        from barekat_genomics.pipeline.runners import get_runner
        import pytest

        with pytest.raises(ValueError, match="ناشناخته"):
            get_runner("unknown")


class TestInterpretationWithCacheDisabled:
    def test_interpret_variants_still_works(self):
        from barekat_genomics.pipeline.variant_calling import call_variants

        variants = call_variants("/fake/path.bam", "BAM")
        results = interpret_variants(variants[:2], genome_build="GRCh38")
        assert len(results) == 2
