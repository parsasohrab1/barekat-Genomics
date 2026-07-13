"""کانکتور تجهیز — نرم‌افزار رایج HIS ایران."""

from __future__ import annotations

import httpx

from barekat_genomics.core.config import get_settings
from barekat_genomics.ehr.connectors.base import EHRConnector
from barekat_genomics.ehr.models import ConnectorResult, EHRContext


class TajhizConnector(EHRConnector):
    """
    اتصال به سامانه تجهیز (HIS).

    در حالت production پیام FHIR Bundle یا HL7 ORU را به API تجهیز ارسال می‌کند.
    بدون تنظیم URL، حالت dry-run فعال است.
    """

    name = "tajhiz"
    display_name = "Tajhiz HIS"
    display_name_fa = "تجهیز"
    supported_formats = ("fhir", "hl7", "json")

    def push(self, ctx: EHRContext, payload: str | dict, fmt: str) -> ConnectorResult:
        settings = get_settings()
        api_url = settings.tajhiz_api_url.rstrip("/")

        body = {
            "patientId": ctx.patient_ehr_id,
            "externalPatientId": ctx.patient_external_id,
            "reportId": ctx.report_id,
            "format": fmt,
            "source": "barekat-genomics",
            "payload": payload if fmt == "json" else None,
            "fhirBundle": payload if fmt == "fhir" else None,
            "hl7Message": payload if fmt == "hl7" else None,
        }

        if not api_url:
            return ConnectorResult(
                success=True,
                connector=self.name,
                format=fmt,
                message="dry-run: تجهیز — URL پیکربندی نشده",
                external_id=f"TAJ-DRY-{ctx.report_id or ctx.patient_ehr_id}",
                details={"mode": "dry_run", "endpoint": None},
            )

        headers = {"Content-Type": "application/json"}
        if settings.tajhiz_api_key:
            headers["X-API-Key"] = settings.tajhiz_api_key

        try:
            with httpx.Client(timeout=settings.ehr_connector_timeout) as client:
                response = client.post(f"{api_url}/api/v1/genomics/import", json=body, headers=headers)
                response.raise_for_status()
                data = response.json() if response.content else {}
                return ConnectorResult(
                    success=True,
                    connector=self.name,
                    format=fmt,
                    message="ارسال موفق به تجهیز",
                    external_id=data.get("transactionId") or data.get("id"),
                    details=data,
                )
        except httpx.HTTPError as exc:
            return ConnectorResult(
                success=False,
                connector=self.name,
                format=fmt,
                message=f"خطا در ارسال به تجهیز: {exc}",
                details={"error": str(exc)},
            )
