"""SEPAS connector — national electronic health exchange."""

from __future__ import annotations

import httpx

from barekat_genomics.core.config import get_settings
from barekat_genomics.ehr.connectors.base import EHRConnector
from barekat_genomics.ehr.models import ConnectorResult, EHRContext


class SepasConnector(EHRConnector):
    """
    Connection to the SEPAS system.

    Sends a FHIR Bundle in the standard SEPAS wrapper for DiagnosticReport and MedicationRequest.
    """

    name = "sepas"
    display_name = "SEPAS"
    display_name_fa = "SEPAS"
    supported_formats = ("fhir", "json")

    def push(self, ctx: EHRContext, payload: str | dict, fmt: str) -> ConnectorResult:
        if fmt == "hl7":
            return ConnectorResult(
                success=False,
                connector=self.name,
                format=fmt,
                message="SEPAS does not support HL7 v2 — use FHIR",
            )

        settings = get_settings()
        api_url = settings.sepas_api_url.rstrip("/")

        envelope = {
            "system": "SEPAS",
            "version": "1.0",
            "messageType": "GenomicDiagnosticReport",
            "nationalPatientId": ctx.patient_ehr_id,
            "localPatientId": ctx.patient_external_id,
            "reportId": ctx.report_id,
            "issuedAt": ctx.issued_at.isoformat(),
            "content": payload,
            "contentType": "application/fhir+json" if fmt == "fhir" else "application/json",
        }

        if not api_url:
            return ConnectorResult(
                success=True,
                connector=self.name,
                format=fmt,
                message="dry-run: SEPAS — URL not configured",
                external_id=f"SEPAS-DRY-{ctx.report_id or ctx.patient_ehr_id}",
                details={"mode": "dry_run", "envelope_keys": list(envelope.keys())},
            )

        headers = {"Content-Type": "application/json"}
        if settings.sepas_api_key:
            headers["Authorization"] = f"Bearer {settings.sepas_api_key}"

        try:
            with httpx.Client(timeout=settings.ehr_connector_timeout) as client:
                response = client.post(f"{api_url}/exchange/genomics", json=envelope, headers=headers)
                response.raise_for_status()
                data = response.json() if response.content else {}
                return ConnectorResult(
                    success=True,
                    connector=self.name,
                    format=fmt,
                    message="Successfully sent to SEPAS",
                    external_id=data.get("trackingCode") or data.get("messageId"),
                    details=data,
                )
        except httpx.HTTPError as exc:
            return ConnectorResult(
                success=False,
                connector=self.name,
                format=fmt,
                message=f"Error sending to SEPAS: {exc}",
                details={"error": str(exc)},
            )
