"""Tests for AI decision support — summarization and RAG."""

import pytest

from barekat_genomics.ai.guardrails import is_diagnosis_request
from barekat_genomics.ai.rag import answer_variant_question, retrieve_context
from barekat_genomics.ai.summarizer import summarize_report_plain
from barekat_genomics.pipeline.report_builder import build_clinical_report
from barekat_genomics.pipeline.interpretation import generate_drug_recommendations, interpret_variants
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants


class TestGuardrails:
    def test_blocks_diagnosis_question_fa(self):
        assert is_diagnosis_request("آیا بیمار مبتلا به سرطان است؟")

    def test_blocks_diagnosis_question_en(self):
        assert is_diagnosis_request("Does the patient have cancer?")

    def test_allows_pgx_question(self):
        assert not is_diagnosis_request("اثر rs4244285 روی کلوپیدوگرل چیست؟")


class TestPlainSummarizer:
    def test_summarize_includes_disclaimer(self):
        variants = call_variants("/fake.bam", "BAM")
        interps = interpret_variants(variants)
        drugs = generate_drug_recommendations(interps)
        clinical = build_clinical_report(interps, drugs, patient_external_id="P-TEST")
        result = summarize_report_plain(clinical, patient_label="P-TEST")
        assert result["decision_support_only"] is True
        assert "تشخیص" in result["disclaimer"] or "قضاوت" in result["disclaimer"]
        assert len(result["plain_summary"]) >= 3
        assert "P-TEST" in result["plain_summary_text"]


class TestRAG:
    def test_retrieve_by_rsid(self):
        v = CalledVariant("chr10", 96521657, "C", "T", "SNP", 90.0, 30.0, "rs4244285")
        chunks, sources = retrieve_context("rs4244285 و کلوپیدوگرل", variant=v)
        assert chunks
        assert any("CYP2C19" in c or "clopidogrel" in c for c in chunks)

    def test_answer_variant_question(self):
        result = answer_variant_question(
            "سطح PharmGKB برای rs4244285 چیست؟",
            variant=CalledVariant("chr10", 96521657, "C", "T", "SNP", 90.0, 30.0, "rs4244285"),
        )
        assert result["decision_support_only"] is True
        assert result["answer_fa"]
        assert not result["blocked"]

    def test_diagnosis_redirect(self):
        result = answer_variant_question("آیا بیمار قطعاً مبتلا به بیماری X است؟")
        assert result["blocked"] is True
        assert "تشخیص" in result["answer_fa"]


class TestAIAPI:
    def test_disclaimer_endpoint(self, client):
        r = client.get("/api/v1/ai/disclaimer")
        assert r.status_code == 200
        assert r.json()["decision_support_only"] is True

    def test_variant_ask_by_rsid(self, client):
        r = client.post(
            "/api/v1/ai/variants/ask",
            json={"question": "اثر rs4244285 بر clopidogrel", "rs_id": "rs4244285"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["decision_support_only"] is True
        assert data["sources"]

    def test_variant_ask_blocks_diagnosis(self, client):
        r = client.post(
            "/api/v1/ai/variants/ask",
            json={"question": "آیا بیمار مبتلا به سرطان است؟", "rs_id": "rs4244285"},
        )
        assert r.status_code == 200
        assert r.json()["blocked"] is True
