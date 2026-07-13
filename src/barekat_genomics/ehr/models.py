"""مدل‌های داخلی برای خروجی EHR."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EHRContext:
    """داده‌های یکپارچه برای تولید FHIR، HL7 و ارسال به کانکتور."""

    patient_ehr_id: str
    patient_external_id: str
    report_id: str | None
    report_type: str
    report_summary: str | None
    clinical_content: dict | None
    variants: list
    drug_recommendations: dict | None
    issued_at: datetime
    organization_id: str = "barekat-genomics"
    genome_build: str = "GRCh38"


@dataclass
class ConnectorResult:
    success: bool
    connector: str
    format: str
    message: str
    external_id: str | None = None
    details: dict = field(default_factory=dict)
