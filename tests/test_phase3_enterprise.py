"""Phase 3 enterprise: RBAC product roles, EHR import, multi-tenant, billing, compliance."""

from barekat_genomics.core.rbac import Permission, Role, has_permission, is_physician_role, is_privileged_role
from barekat_genomics.ehr.import_fhir import parse_fhir_patient_bundle
from barekat_genomics.ehr.import_hl7 import parse_hl7_message
from barekat_genomics.compliance.checklist import checklist_as_dicts, summary_counts


class TestPhase3RBAC:
    def test_product_roles(self):
        assert has_permission("admin", Permission.USERS_MANAGE)
        assert has_permission("analyst", Permission.REPORTS_APPROVE)
        assert has_permission("physician", Permission.REPORTS_READ_OWN)
        assert not has_permission("physician", Permission.REPORTS_APPROVE)
        assert has_permission("geneticist", Permission.EHR_IMPORT)
        assert is_physician_role("physician")
        assert is_physician_role("clinician")
        assert is_privileged_role("analyst")

    def test_legacy_roles_still_work(self):
        for role in Role:
            assert role in __import__("barekat_genomics.core.rbac", fromlist=["ROLE_PERMISSIONS"]).ROLE_PERMISSIONS


class TestPhase3EHRImport:
    def test_parse_fhir_patient(self):
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "p1",
                        "identifier": [{"value": "EXT-99"}],
                        "name": [{"family": "Karimi", "given": ["Ali"]}],
                        "gender": "male",
                    }
                }
            ],
        }
        parsed = parse_fhir_patient_bundle(bundle)
        assert parsed["external_id"] == "EXT-99"
        assert "Ali" in (parsed["full_name"] or "")
        assert parsed["gender"] == "male"

    def test_parse_hl7_pid(self):
        msg = (
            "MSH|^~\\&|HIS|HOSP|BAREKAT|LAB|202601011200||ADT^A04|1|P|2.5\r"
            "PID|1||PID123^^^HOSP||Karimi^Ali||19900101|M\r"
        )
        parsed = parse_hl7_message(msg)
        assert parsed["external_id"] == "PID123"
        assert parsed["gender"] == "male"


class TestPhase3API:
    def test_compliance_checklist(self, client):
        res = client.get("/api/v1/compliance/checklist")
        assert res.status_code == 200
        body = res.json()
        assert body["summary"]["total"] >= 10
        assert any(i["id"] == "auth-rbac" for i in body["items"])

    def test_organizations_me(self, client):
        res = client.get("/api/v1/organizations/me")
        assert res.status_code == 200
        assert res.json()["slug"] == "default"

    def test_billing_plans_and_subscribe(self, client):
        plans = client.get("/api/v1/billing/plans")
        assert plans.status_code == 200
        assert len(plans.json()) >= 2
        sub = client.post("/api/v1/billing/subscribe", json={"plan_code": "starter", "trial_days": 7})
        assert sub.status_code == 200
        assert sub.json()["status"] in ("trial", "active")
        usage = client.get("/api/v1/billing/usage")
        assert usage.status_code == 200
        assert "samples_limit" in usage.json()

    def test_ehr_fhir_import(self, client):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "fhir-1",
                        "identifier": [{"value": "IMP-001"}],
                        "name": [{"family": "Test", "given": ["PGx"]}],
                        "gender": "female",
                    }
                }
            ],
        }
        res = client.post("/api/v1/ehr/import/fhir", json=bundle)
        assert res.status_code == 200
        assert res.json()["created"] is True
        assert res.json()["external_id"] == "IMP-001"

    def test_ehr_hl7_import(self, client):
        msg = (
            "MSH|^~\\&|HIS|HOSP|BAREKAT|LAB|202601011200||ADT^A04|1|P|2.5\r"
            "PID|1||HL7-77^^^HOSP||Ahmadi^Sara||19880101|F\r"
        )
        res = client.post("/api/v1/ehr/import/hl7", json={"message": msg})
        assert res.status_code == 200
        assert res.json()["external_id"] == "HL7-77"

    def test_create_user_admin(self, client):
        res = client.post(
            "/api/v1/users/",
            json={
                "email": "analyst1@barekat.local",
                "password": "password123",
                "full_name": "Analyst One",
                "role": "analyst",
            },
        )
        assert res.status_code == 201
        assert res.json()["role"] == "analyst"

    def test_multi_tenant_isolation(self, client, db_session):
        from barekat_genomics.services.organization_service import OrganizationService
        from barekat_genomics.services.patient_service import PatientService
        from barekat_genomics.schemas import PatientCreate

        svc = OrganizationService(db_session)
        other = svc.create(slug="clinic-b", name="Clinic B", deployment_mode="saas")
        PatientService(db_session).create(
            PatientCreate(external_id="ISO-A", name="A"),
            organization_id=svc.ensure_default().id,
        )
        PatientService(db_session).create(
            PatientCreate(external_id="ISO-B", name="B"),
            organization_id=other.id,
        )
        listed = client.get("/api/v1/patients/")
        assert listed.status_code == 200
        ext_ids = {p["external_id"] for p in listed.json()}
        assert "ISO-A" in ext_ids
        assert "ISO-B" not in ext_ids


class TestPhase3ComplianceModule:
    def test_summary_counts(self):
        s = summary_counts()
        assert s["total"] == len(checklist_as_dicts())
        assert s["implemented"] >= 1
