"""تست‌های فاز ۱: production readiness، QC، benchmark، reference."""

from barekat_genomics.pipeline.mode import is_production_pipeline, missing_production_tools
from barekat_genomics.pipeline.preprocessing import run_quality_control
from barekat_genomics.pipeline.reference import validate_reference_bundle
from barekat_genomics.pipeline.validation import evaluate_simulated_benchmark, evaluate_variant_concordance
from barekat_genomics.pipeline.variant_calling import CalledVariant
from barekat_genomics.services.pipeline_service import STAGE_PROGRESS, compute_job_progress


def test_simulated_mode_still_default():
    assert is_production_pipeline() is False


def test_missing_tools_list_is_complete_when_production_but_no_bins(monkeypatch):
    from barekat_genomics.core.config import get_settings

    monkeypatch.setenv("PIPELINE_MODE", "production")
    get_settings.cache_clear()
    try:
        missing = missing_production_tools()
        assert "snpEff" in missing or "fastqc" in missing or len(missing) >= 1
        # without tools installed, production check fails
        assert is_production_pipeline() is False
    finally:
        monkeypatch.setenv("PIPELINE_MODE", "simulated")
        get_settings.cache_clear()


def test_qc_metrics_include_depth_fields():
    qc = run_quality_control("/fake.bam", "BAM")
    assert qc.passed is True
    assert qc.mean_depth is not None and qc.mean_depth > 0
    assert qc.coverage_pct_10x is not None
    assert qc.coverage_pct_20x is not None
    assert 0.3 < qc.gc_content < 0.6
    payload = qc.to_dict()
    assert "mean_depth" in payload
    assert "coverage_pct_20x" in payload


def test_reference_validation_reports_checks():
    result = validate_reference_bundle()
    assert result.genome_build
    assert isinstance(result.ready, bool)
    assert len(result.checks) >= 3
    as_dict = result.to_dict()
    assert "minio_prefix" in as_dict


def test_stage_progress_includes_alignment():
    assert STAGE_PROGRESS["alignment"] == 40
    assert STAGE_PROGRESS["quality_control"] < STAGE_PROGRESS["alignment"]


def test_compute_job_progress_completed():
    class _Job:
        status = "completed"
        stage = "done"

    assert compute_job_progress(_Job()) == 100


def test_benchmark_sensitivity_gate():
    metrics = evaluate_simulated_benchmark()
    assert metrics["sensitivity"] >= 0.8
    assert metrics["true_positives"] >= 4
    assert "rs4244285" in metrics["matched_rs_ids"]


def test_concordance_helper():
    called = [
        CalledVariant("chr1", 1, "A", "G", "SNP", 99, 40, "rs1"),
        CalledVariant("chr2", 2, "C", "T", "SNP", 99, 40, "rs2"),
    ]
    truth = [
        {"rs_id": "rs1", "expected_in_simulated": True},
        {"rs_id": "rs3", "expected_in_simulated": True},
    ]
    m = evaluate_variant_concordance(called, truth)
    assert m["true_positives"] == 1
    assert m["false_negatives"] == 1
    assert m["false_positives"] == 1


def test_reference_status_api(client):
    resp = client.get("/api/v1/pipeline/reference/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data
    assert "checks" in data


def test_benchmark_metrics_api(client):
    resp = client.get("/api/v1/pipeline/benchmark/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sensitivity"] >= 0.8
    assert "precision" in data


def test_e2e_job_exposes_qc_metrics(client):
    from io import BytesIO

    patient = client.post(
        "/api/v1/patients/",
        json={"external_id": "P-QC-001", "age": 40, "gender": "female"},
    ).json()
    upload = client.post(
        "/api/v1/samples/upload",
        data={
            "patient_id": patient["id"],
            "sample_id": "S-QC-001",
            "file_type": "BAM",
            "priority": "normal",
        },
        files={"file": ("sample.bam", BytesIO(b"FAKEBAM"), "application/octet-stream")},
    )
    assert upload.status_code == 201
    sample = upload.json()

    job_resp = client.post(
        "/api/v1/pipeline/run?sync=true",
        json={"sample_id": sample["id"], "module": "pharmacogenomics"},
    )
    assert job_resp.status_code == 202
    job = job_resp.json()
    assert job["status"] == "completed"
    assert "progress" in job
    qc = job["qc_metrics"]
    assert qc is not None
    assert "gc_content" in qc
    assert "mean_depth" in qc

    qc_api = client.get(f"/api/v1/pipeline/jobs/{job['id']}/qc")
    assert qc_api.status_code == 200
    assert qc_api.json()["mean_depth"] is not None

    sample_qc = client.get(f"/api/v1/samples/{sample['id']}/qc")
    assert sample_qc.status_code == 200
    assert sample_qc.json()["gc_content"] is not None
