"""Tests for observability: metrics, health probes."""

from barekat_genomics.core.observability.metrics import (
    QC_CHECKS_TOTAL,
    PIPELINE_JOBS_TOTAL,
    record_pipeline_finish,
    record_qc_result,
)


class TestMetrics:
    def test_record_qc_result(self):
        before = QC_CHECKS_TOTAL.labels(result="passed")._value.get()
        record_qc_result(True)
        after = QC_CHECKS_TOTAL.labels(result="passed")._value.get()
        assert after >= before + 1

    def test_record_pipeline_finish(self):
        before = PIPELINE_JOBS_TOTAL.labels(
            status="completed", priority="normal", backend="celery"
        )._value.get()
        record_pipeline_finish(
            status="completed",
            priority="normal",
            backend="celery",
            duration_seconds=12.5,
            variant_count=3,
        )
        after = PIPELINE_JOBS_TOTAL.labels(
            status="completed", priority="normal", backend="celery"
        )._value.get()
        assert after >= before + 1


class TestHealthEndpoints:
    def test_liveness(self, client):
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "barekat_pipeline_jobs_total" in response.text

    def test_health_full(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "version" in data
        assert "services" in data
