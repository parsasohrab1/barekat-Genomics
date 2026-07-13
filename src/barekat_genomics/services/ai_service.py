"""سرویس دستیار پشتیبان تصمیم."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.ai.rag import answer_variant_question
from barekat_genomics.ai.summarizer import summarize_report_plain
from barekat_genomics.core.config import get_settings
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.pipeline.variant_calling import CalledVariant
from barekat_genomics.services.report_service import ReportService


class AIAssistService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reports = ReportService(db)

    def is_enabled(self) -> bool:
        return get_settings().ai_assist_enabled

    def plain_summary_for_report(self, report_id: uuid.UUID) -> dict:
        report = self.reports.get_report(report_id)
        if not report:
            raise ValueError("گزارش یافت نشد")

        patient = self.db.query(Patient).filter(Patient.id == report.patient_id).first()
        clinical = self.reports.get_clinical_content(report)
        result = summarize_report_plain(
            clinical,
            patient_label=patient.external_id if patient else None,
        )
        result["report_id"] = str(report_id)
        return result

    def ask_about_variant(
        self,
        question: str,
        *,
        variant_id: uuid.UUID | None = None,
        rs_id: str | None = None,
    ) -> dict:
        variant: CalledVariant | None = None
        annotation: dict | None = None

        if variant_id:
            row = (
                self.db.query(Variant, VariantAnnotation)
                .outerjoin(VariantAnnotation, VariantAnnotation.variant_id == Variant.id)
                .filter(Variant.id == variant_id)
                .first()
            )
            if not row:
                raise ValueError("واریانت یافت نشد")
            v, ann = row
            variant = CalledVariant(
                chromosome=v.chromosome,
                position=v.position,
                ref_allele=v.ref_allele,
                alt_allele=v.alt_allele,
                variant_type=v.variant_type,
                quality_score=v.quality_score or 0.0,
                depth=v.depth or 30,
                rs_id=v.rs_id,
            )
            if ann:
                annotation = {
                    "gene": ann.gene,
                    "interpretation": ann.interpretation,
                    "clinical_significance": ann.clinical_significance,
                    "pharmacogenomic_effect": ann.pharmacogenomic_effect,
                }
        elif rs_id:
            rs = rs_id if rs_id.startswith("rs") else f"rs{rs_id}"
            variant = CalledVariant("chr1", 0, "N", "N", "SNP", 0.0, 0, rs)

        result = answer_variant_question(question, variant=variant, annotation=annotation)
        if variant_id:
            result["variant_id"] = str(variant_id)
        if rs_id:
            result["rs_id"] = rs_id
        return result
