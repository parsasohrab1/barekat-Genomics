"""Phase 4: cohort discovery, assay workflow, partner API, cache, IP assets."""

from pathlib import Path

from barekat_genomics.pipeline.assay_config import ASSAY_TYPES, FILE_TYPES, get_assay_profile
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.services.cohort_service import load_iranian_af
from barekat_genomics.services.knowledge_asset_service import KnowledgeAssetService
from barekat_genomics.services.result_cache_service import (
    ComputeCostService,
    build_pipeline_cache_key,
    content_hash_for_path,
)


class TestPhase4Assay:
    def test_assay_profiles(self):
        assert set(ASSAY_TYPES) == {"wgs", "wes", "panel"}
        assert "VCF" in FILE_TYPES
        wes = get_assay_profile("wes")
        assert wes.haplotyper_intervals is True
        assert get_assay_profile("wgs").haplotyper_intervals is False

    def test_vcf_panel_pipeline(self, tmp_path):
        vcf = tmp_path / "demo.vcf"
        vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        result = run_full_pipeline(str(vcf), "VCF", assay_type="panel", sample_label="p4-vcf")
        assert result.success is True
        assert result.clinical_content.get("assay", {}).get("assay_type") == "panel"
        assert len(result.variants) >= 1


class TestPhase4IranianAf:
    def test_load_iranian_af(self):
        data = load_iranian_af()
        assert "rs4244285" in data
        assert data["rs4244285"]["af"] > 0


class TestPhase4CohortAPI:
    def test_create_and_discover_empty(self, client):
        created = client.post(
            "/api/v1/cohorts/",
            json={
                "code": "IR-PGX-01",
                "name": "Iranian PGx Pilot",
                "name_fa": "کوهورت پایلوت ایرانی",
                "population": "iranian",
            },
        )
        assert created.status_code == 201
        cohort_id = created.json()["id"]
        disc = client.get(f"/api/v1/cohorts/{cohort_id}/discovery")
        assert disc.status_code == 200
        body = disc.json()
        assert body["population"] == "iranian"
        assert body["n_samples"] == 0
        assert body["markers"] == []

    def test_iranian_af_meta(self, client):
        res = client.get("/api/v1/cohorts/meta/iranian-af")
        assert res.status_code == 200
        assert res.json()["n_markers"] >= 5


class TestPhase4PartnerAPI:
    def test_create_key_and_health(self, client):
        key_res = client.post(
            "/api/v1/integrations/api-keys",
            json={"name": "lab-a", "rate_limit_per_minute": 120},
        )
        assert key_res.status_code == 201
        raw = key_res.json()["api_key"]
        assert raw.startswith("bk_live_")
        health = client.get("/api/v1/partner/health", headers={"X-API-Key": raw})
        assert health.status_code == 200
        assert "VCF" in health.json()["supported_file_types"]

    def test_partner_pipeline_with_cache(self, client, tmp_path):
        key_res = client.post(
            "/api/v1/integrations/api-keys",
            json={"name": "lab-cache", "scopes": "pipeline:run,samples:write"},
        )
        raw = key_res.json()["api_key"]
        vcf = tmp_path / "partner.vcf"
        vcf.write_text("##fileformat=VCFv4.2\n")
        payload = {
            "file_path": str(vcf),
            "file_type": "VCF",
            "assay_type": "wes",
            "use_cache": True,
            "sample_label": "partner-1",
        }
        first = client.post(
            "/api/v1/partner/pipeline/run",
            json=payload,
            headers={"X-API-Key": raw},
        )
        assert first.status_code == 200
        assert first.json()["cache_hit"] is False
        assert first.json()["result"]["success"] is True
        second = client.post(
            "/api/v1/partner/pipeline/run",
            json=payload,
            headers={"X-API-Key": raw},
        )
        assert second.status_code == 200
        assert second.json()["cache_hit"] is True
        assert second.json()["estimate"]["cache_hit"] is True


class TestPhase4ComputeAndIP:
    def test_compute_summary(self, client):
        res = client.get("/api/v1/integrations/compute/summary")
        assert res.status_code == 200
        assert "cost" in res.json()
        assert "pipeline_cache" in res.json()

    def test_knowledge_assets(self, client, db_session):
        assets = client.get("/api/v1/knowledge-assets/")
        assert assets.status_code == 200
        codes = {a["asset_code"] for a in assets.json()}
        assert "BG-ML-VCF-V2" in codes
        assert "BG-METHOD-IR-COHORT" in codes
        assert "BG-KIT-PGX-WORKFLOW" in codes

    def test_cost_estimate_cache_discount(self, db_session):
        svc = ComputeCostService(db_session)
        full = svc.estimate("wgs", cache_hit=False)
        cached = svc.estimate("wgs", cache_hit=True)
        assert cached["estimated_usd"] < full["estimated_usd"]

    def test_cache_key_stable(self, tmp_path):
        f = tmp_path / "x.vcf"
        f.write_bytes(b"abc")
        h = content_hash_for_path(f)
        k1 = build_pipeline_cache_key(
            content_hash=h, file_type="VCF", assay_type="panel", genome_build="GRCh38", module_id="pgx"
        )
        k2 = build_pipeline_cache_key(
            content_hash=h, file_type="VCF", assay_type="panel", genome_build="GRCh38", module_id="pgx"
        )
        assert k1 == k2
        assert k1.startswith("pipe:")
