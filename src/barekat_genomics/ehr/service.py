"""سرویس یکپارچه‌سازی EHR."""

from __future__ import annotations

from datetime import datetime, timezone

from barekat_genomics.core.config import get_settings
from barekat_genomics.ehr.connectors.registry import get_connector, list_connectors
from barekat_genomics.ehr.fhir_r4 import build_fhir_bundle
from barekat_genomics.ehr.hl7_v2 import build_oru_message
from barekat_genomics.ehr.models import ConnectorResult, EHRContext
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.schemas import EHRVariantExport


class EHRIntegrationService:
    def build_context(
        self,
        patient: Patient,
        export: EHRVariantExport,
        report: GenomicReport | None = None,
    ) -> EHRContext:
        settings = get_settings()
        issued = report.finalized_at or report.approved_at if report else None
        if issued is None:
            issued = datetime.now(timezone.utc)

        return EHRContext(
            patient_ehr_id=export.patient_ehr_id,
            patient_external_id=patient.external_id,
            report_id=str(report.id) if report else (str(export.report_id) if export.report_id else None),
            report_type=report.report_type if report else "pharmacogenomic",
            report_summary=export.report_summary,
            clinical_content=export.clinical_content,
            variants=export.variants,
            drug_recommendations=export.drug_recommendations,
            issued_at=issued,
            organization_id=settings.ehr_fhir_organization_id,
            genome_build=settings.genome_build,
        )

    def export_fhir(self, ctx: EHRContext) -> dict:
        return build_fhir_bundle(ctx)

    def export_hl7(self, ctx: EHRContext) -> str:
        settings = get_settings()
        return build_oru_message(ctx, receiving_facility=settings.ehr_hl7_receiving_facility)

    def export_json(self, export: EHRVariantExport) -> dict:
        return export.model_dump(mode="json")

    def push(
        self,
        ctx: EHRContext,
        export: EHRVariantExport,
        connector_name: str,
        fmt: str,
    ) -> ConnectorResult:
        connector = get_connector(connector_name)
        if not connector:
            return ConnectorResult(
                success=False,
                connector=connector_name,
                format=fmt,
                message=f"کانکتور ناشناخته: {connector_name}",
            )

        if fmt not in connector.supported_formats:
            return ConnectorResult(
                success=False,
                connector=connector_name,
                format=fmt,
                message=f"فرمت {fmt} برای {connector_name} پشتیبانی نمی‌شود",
            )

        if fmt == "fhir":
            payload = self.export_fhir(ctx)
        elif fmt == "hl7":
            payload = self.export_hl7(ctx)
        else:
            payload = self.export_json(export)

        return connector.push(ctx, payload, fmt)

    def list_connectors(self) -> list[dict]:
        return list_connectors()
