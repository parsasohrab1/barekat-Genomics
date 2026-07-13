"""Tests for incremental diagnostic modules."""

from barekat_genomics.modules.analyzer import analyze_module, result_to_dict
from barekat_genomics.modules.panels import (
    CARRIER_SCREENING_GENES,
    CGP_ACTIONABLE_GENES,
    CPIC_PANEL_GENES,
)
from barekat_genomics.modules.registry import DEFAULT_MODULE, get_module, list_modules
from barekat_genomics.pipeline.interpretation import VariantInterpretation
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.pipeline.variant_calling import CalledVariant


def _interp(
    gene: str,
    *,
    sig: str = "pathogenic",
    ml: float = 0.85,
) -> tuple[CalledVariant, VariantInterpretation]:
    v = CalledVariant("chr1", 1000, "A", "G", "SNP", 90.0, 30.0, "rs123")
    i = VariantInterpretation(
        gene=gene,
        consequence="missense",
        clinical_significance=sig,
        pharmacogenomic_effect=None,
        priority_score=ml,
        ml_score=ml,
        ml_confidence=0.9,
        interpretation=f"test {gene}",
        knowledge_sources=["test"],
    )
    return v, i


class TestModuleRegistry:
    def test_list_modules_has_six(self):
        mods = list_modules()
        assert len(mods) == 6
        ids = {m.id for m in mods}
        assert "cgp" in ids
        assert "carrier_screening" in ids
        assert "pgx_panel" in ids
        assert "tumor_normal" in ids
        assert "prs" in ids

    def test_default_module(self):
        assert DEFAULT_MODULE == "pharmacogenomics"

    def test_unknown_module_raises(self):
        import pytest

        with pytest.raises(ValueError, match="ناشناخته"):
            get_module("invalid")

    def test_cpic_panel_has_at_least_12_genes(self):
        assert len(CPIC_PANEL_GENES) >= 12

    def test_cgp_panel_has_actionable_genes(self):
        assert "BRCA1" in CGP_ACTIONABLE_GENES
        assert "TP53" in CGP_ACTIONABLE_GENES

    def test_carrier_panel_includes_cftr(self):
        assert "CFTR" in CARRIER_SCREENING_GENES


class TestModuleAnalyzer:
    def test_pgx_panel_filters_genes(self):
        interps = [
            _interp("CYP2D6"),
            _interp("BRCA1"),
            _interp("MTHFR", sig="benign", ml=0.1),
        ]
        result = analyze_module("pgx_panel", interps)
        assert result.module_id == "pgx_panel"
        assert all(f.gene in CPIC_PANEL_GENES for f in result.findings)
        assert any(f.gene == "CYP2D6" for f in result.findings)

    def test_cgp_finds_oncology_genes(self):
        interps = [_interp("BRCA1"), _interp("CYP2D6")]
        result = analyze_module("cgp", interps)
        assert len(result.findings) == 1
        assert result.findings[0].gene == "BRCA1"

    def test_carrier_screening(self):
        interps = [_interp("CFTR"), _interp("CYP2D6")]
        result = analyze_module("carrier_screening", interps)
        assert len(result.findings) == 1
        assert result.findings[0].extra.get("carrier_status") == "likely_carrier"

    def test_tumor_normal_somatic_vs_germline(self):
        somatic_v = CalledVariant("chr17", 43044295, "G", "A", "SNP", 90.0, 30.0, "rs123")
        somatic_i = VariantInterpretation(
            gene="BRCA1",
            consequence="missense",
            clinical_significance="pathogenic",
            pharmacogenomic_effect=None,
            priority_score=0.9,
            ml_score=0.9,
            ml_confidence=0.9,
            interpretation="somatic",
            knowledge_sources=["test"],
        )
        shared_v = CalledVariant("chr22", 29091841, "G", "A", "SNP", 90.0, 30.0, "rs555607708")
        shared_i = VariantInterpretation(
            gene="CHEK2",
            consequence="missense",
            clinical_significance="pathogenic",
            pharmacogenomic_effect=None,
            priority_score=0.8,
            ml_score=0.8,
            ml_confidence=0.9,
            interpretation="germline",
            knowledge_sources=["test"],
        )
        result = analyze_module(
            "tumor_normal",
            [(somatic_v, somatic_i), (shared_v, shared_i)],
            normal_interpretations=[(shared_v, shared_i)],
        )
        origins = {f.extra.get("origin") for f in result.findings}
        assert "somatic" in origins
        assert "germline" in origins

    def test_prs_returns_trait_scores(self):
        v = CalledVariant("chr9", 1, "A", "G", "SNP", 90.0, 30.0, "rs10757274")
        i = VariantInterpretation(
            gene=None,
            consequence="intergenic",
            clinical_significance="benign",
            pharmacogenomic_effect=None,
            priority_score=0.5,
            ml_score=0.9,
            ml_confidence=0.8,
            interpretation="prs snp",
            knowledge_sources=["test"],
        )
        result = analyze_module("prs", [(v, i)])
        assert "prs_scores" in result.metadata
        assert len(result.metadata["prs_scores"]) >= 4

    def test_result_to_dict_serializable(self):
        result = analyze_module("pgx_panel", [_interp("CYP2D6")])
        d = result_to_dict(result)
        assert d["module_id"] == "pgx_panel"
        assert "findings" in d


class TestModulePipelineIntegration:
    def test_full_pipeline_with_cgp_module(self):
        result = run_full_pipeline("/fake/path.bam", "BAM", module_id="cgp")
        assert result.success is True
        assert result.module_analysis is not None
        assert result.module_analysis["module_id"] == "cgp"
        assert "module_analysis" in result.clinical_content

    def test_modules_api(self, client):
        response = client.get("/api/v1/pipeline/modules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
        assert any(m["id"] == "pgx_panel" for m in data)
