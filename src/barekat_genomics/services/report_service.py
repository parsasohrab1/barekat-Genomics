"""سرویس گزارش‌های ژنومی."""

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.models.report import GenomicReport
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.schemas import EHRVariantExport, VariantWithAnnotation, VariantAnnotationResponse


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_report(self, report_id: uuid.UUID) -> GenomicReport | None:
        return self.db.query(GenomicReport).filter(GenomicReport.id == report_id).first()

    def list_by_patient(self, patient_id: uuid.UUID) -> list[GenomicReport]:
        return (
            self.db.query(GenomicReport)
            .filter(GenomicReport.patient_id == patient_id)
            .order_by(GenomicReport.created_at.desc())
            .all()
        )

    def get_patient_variants(self, patient_id: uuid.UUID) -> list[VariantWithAnnotation]:
        samples = (
            self.db.query(SequencingSample)
            .filter(SequencingSample.patient_id == patient_id)
            .all()
        )
        sample_ids = [s.id for s in samples]
        variants = self.db.query(Variant).filter(Variant.sample_id.in_(sample_ids)).all()

        result = []
        for v in variants:
            annotations = (
                self.db.query(VariantAnnotation)
                .filter(VariantAnnotation.variant_id == v.id)
                .all()
            )
            result.append(VariantWithAnnotation(
                id=v.id,
                chromosome=v.chromosome,
                position=v.position,
                ref_allele=v.ref_allele,
                alt_allele=v.alt_allele,
                variant_type=v.variant_type,
                quality_score=v.quality_score,
                rs_id=v.rs_id,
                annotations=[VariantAnnotationResponse.model_validate(a) for a in annotations],
            ))
        return result

    def export_for_ehr(self, patient_id: uuid.UUID) -> EHRVariantExport | None:
        from barekat_genomics.models.patient import Patient

        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None

        variants = self.get_patient_variants(patient_id)
        latest_report = (
            self.db.query(GenomicReport)
            .filter(GenomicReport.patient_id == patient_id, GenomicReport.status == "completed")
            .order_by(GenomicReport.created_at.desc())
            .first()
        )

        return EHRVariantExport(
            patient_ehr_id=patient.ehr_patient_id or patient.external_id,
            variants=variants,
            drug_recommendations=latest_report.drug_recommendations if latest_report else None,
            report_summary=latest_report.summary if latest_report else None,
        )
