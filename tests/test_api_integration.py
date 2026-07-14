"""تست‌های یکپارچه API و پایپ‌لاین simulated."""

from io import BytesIO


class TestApiIntegration:
    def test_create_and_get_patient(self, client):
        create = client.post(
            "/api/v1/patients/",
            json={"external_id": "P-API-001", "age": 45, "gender": "female"},
        )
        assert create.status_code == 201, create.text
        patient = create.json()
        assert patient["external_id"] == "P-API-001"

        fetched = client.get(f"/api/v1/patients/{patient['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == patient["id"]

        audits = client.get("/api/v1/audit/logs")
        assert audits.status_code == 200
        actions = {row["action"] for row in audits.json()}
        assert "create_patient" in actions
        assert "view_patient" in actions

    def test_settings_endpoint(self, client):
        response = client.get("/api/v1/settings/")
        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_mode"] == "simulated"
        assert data["audit_log_enabled"] is True
        assert data["clinical_report_schema_version"] == "1.0"

    def test_simulated_pipeline_e2e(self, client):
        patient = client.post(
            "/api/v1/patients/",
            json={"external_id": "P-E2E-001", "age": 50, "gender": "male"},
        ).json()

        upload = client.post(
            "/api/v1/samples/upload",
            data={
                "patient_id": patient["id"],
                "sample_id": "S-E2E-001",
                "file_type": "BAM",
                "priority": "normal",
            },
            files={"file": ("sample.bam", BytesIO(b"FAKEBAM"), "application/octet-stream")},
        )
        assert upload.status_code == 201, upload.text
        sample = upload.json()
        assert sample["status"] == "uploaded"

        job_resp = client.post(
            "/api/v1/pipeline/run?sync=true",
            json={"sample_id": sample["id"], "module": "pharmacogenomics"},
        )
        assert job_resp.status_code == 202, job_resp.text
        job = job_resp.json()
        assert job["status"] == "completed"
        assert job["stage"] == "done"
        assert job["qc_metrics"] is not None

        reports = client.get("/api/v1/reports/")
        assert reports.status_code == 200
        report_list = reports.json()
        assert len(report_list) >= 1
        report = report_list[0]
        assert report["patient_id"] == patient["id"]
        content = report.get("clinical_content") or {}
        assert content.get("schema_version") == "1.0"
        assert "executive_summary" in content

        detail = client.get(f"/api/v1/reports/{report['id']}")
        assert detail.status_code == 200

        audits = client.get("/api/v1/audit/logs").json()
        actions = {row["action"] for row in audits}
        assert "upload_sample" in actions
        assert "run_pipeline" in actions
        assert "view_report" in actions
