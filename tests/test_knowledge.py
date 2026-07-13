"""Tests for official knowledge base registry."""

from pathlib import Path

from barekat_genomics.knowledge.registry import KnowledgeRegistry
from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "reference" / "knowledge"


class TestKnowledgeRegistry:
    def test_lookup_by_rsid(self):
        reg = KnowledgeRegistry(KNOWLEDGE_DIR)
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.0, 40, "rs4244285")
        kb = reg.lookup(v)
        assert kb is not None
        assert kb.gene == "CYP2C19"
        assert kb.drug == "clopidogrel"
        assert "PharmGKB" in kb.sources
        assert "dbSNP" in kb.sources
        assert kb.gnomad_af is not None

    def test_cpic_lookup(self):
        reg = KnowledgeRegistry(KNOWLEDGE_DIR)
        info = reg.get_cpic_for_gene_drug("CYP2C9", "warfarin")
        assert info is not None
        assert info["cpic_level"] == "A"

    def test_interpretation_uses_knowledge(self):
        variants = call_variants("/fake/path.bam", "BAM")
        interpretations = interpret_variants(variants)
        recs = generate_drug_recommendations(interpretations)
        assert len(recs) >= 4
        assert "warfarin" in recs
        assert recs["warfarin"]["cpic_level"] == "A"
        assert "CPIC" in recs["warfarin"].get("sources", []) or "PharmGKB" in recs["warfarin"].get("sources", [])

    def test_clinvar_drug_response_maps_to_pathogenic(self):
        reg = KnowledgeRegistry(KNOWLEDGE_DIR)
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.0, 40, "rs4244285")
        kb = reg.lookup(v)
        interpretations = interpret_variants([v])
        _, interp = interpretations[0]
        assert kb.clinical_significance == "drug_response"
        assert interp.clinical_significance == "pathogenic"
