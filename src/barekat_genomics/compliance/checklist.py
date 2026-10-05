"""Regulatory compliance checklist (GDPR-like / Ministry of Health)."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ComplianceItem:
    id: str
    category: str
    title_fa: str
    title_en: str
    status: str  # implemented | partial | planned
    evidence: str
    regulator: str  # GDPR-like | MOH | HIPAA | Internal


COMPLIANCE_CHECKLIST: list[ComplianceItem] = [
    ComplianceItem(
        "auth-rbac",
        "Access Control",
        "Authentication and role-based access control",
        "Authentication and RBAC",
        "implemented",
        "JWT + Role permissions (admin/analyst/physician)",
        "GDPR-like",
    ),
    ComplianceItem(
        "phi-encryption",
        "Confidentiality",
        "Patient name encryption (PHI at rest in app)",
        "PHI field encryption",
        "implemented",
        "Fernet encrypt_phi / decrypt_phi",
        "HIPAA",
    ),
    ComplianceItem(
        "audit-log",
        "Accountability",
        "Access event logging and EHR export",
        "Immutable application audit trail",
        "implemented",
        "AuditLog + /api/v1/audit",
        "MOH",
    ),
    ComplianceItem(
        "multi-tenant",
        "Isolation",
        "Multi-organization data isolation",
        "Multi-tenant data isolation",
        "implemented",
        "Organization + organization_id filters",
        "Internal",
    ),
    ComplianceItem(
        "ehr-standard",
        "Interoperability",
        "FHIR R4 / HL7 v2 standard exchange",
        "Standard EHR export/import",
        "implemented",
        "/ehr/export|/ehr/import fhir+hl7",
        "MOH",
    ),
    ComplianceItem(
        "subject-access",
        "Data Subject Rights",
        "Data subject right of access (patient data export)",
        "Subject access / data portability",
        "implemented",
        "GET /compliance/subjects/{patient_id}/export",
        "GDPR-like",
    ),
    ComplianceItem(
        "erasure",
        "Data Subject Rights",
        "Deletion/anonymization request (partial right to be forgotten)",
        "Erasure / anonymization request",
        "partial",
        "POST /compliance/subjects/{patient_id}/erase (anonymize PHI)",
        "GDPR-like",
    ),
    ComplianceItem(
        "retention",
        "Lifecycle",
        "PHI retention policy (configured days)",
        "Retention policy configuration",
        "partial",
        "phi_retention_days in Settings; purge job planned",
        "HIPAA",
    ),
    ComplianceItem(
        "consent",
        "Lawfulness",
        "Recording of informed patient consent for genetic testing",
        "Informed consent record",
        "planned",
        "Consent entity roadmap",
        "MOH",
    ),
    ComplianceItem(
        "sepas-connectivity",
        "National Health Network",
        "SEPAS / HIS connection readiness",
        "SEPAS / HIS connector readiness",
        "partial",
        "sepas + tajhiz connectors (configurable endpoints)",
        "MOH",
    ),
    ComplianceItem(
        "breach-notify",
        "Incident",
        "Data breach notification procedures",
        "Breach notification process",
        "planned",
        "Operator runbook + escalation",
        "GDPR-like",
    ),
    ComplianceItem(
        "dpiA",
        "Privacy by Design",
        "Data protection impact assessment (DPIA)",
        "Data Protection Impact Assessment",
        "planned",
        "Template in COMPLIANCE_CHECKLIST.md",
        "GDPR-like",
    ),
]


def checklist_as_dicts() -> list[dict]:
    return [asdict(i) for i in COMPLIANCE_CHECKLIST]


def summary_counts() -> dict[str, int]:
    counts = {"implemented": 0, "partial": 0, "planned": 0}
    for item in COMPLIANCE_CHECKLIST:
        counts[item.status] = counts.get(item.status, 0) + 1
    counts["total"] = len(COMPLIANCE_CHECKLIST)
    return counts
