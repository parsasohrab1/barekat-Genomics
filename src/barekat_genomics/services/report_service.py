"""سرویس گزارش‌های ژنومی."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from barekat_genomics.core.rbac import Role, is_privileged_role
from barekat_genomics.core.review import REPORT_STATUS_COMPLETED, REPORT_STATUS_PENDING_FINAL
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.user import User
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.pipeline.report_builder import rebuild_clinical_content_from_db
from barekat_genomics.schemas import EHRVariantExport, VariantAnnotationResponse, VariantWithAnnotation
from barekat_genomics.services.pdf_service import compute_report_signature, generate_clinical_pdf
from barekat_genomics.services.review_service import ReviewService


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.review = ReviewService(db)

    def get_report(self, report_id: uuid.UUID) -> GenomicReport | None:
        return self.db.query(GenomicReport).filter(GenomicReport.id == report_id).first()

    def get_clinical_content(self, report: GenomicReport, *, refresh: bool = False) -> dict:
        if report.clinical_content and not refresh and report.status == REPORT_STATUS_COMPLETED:
            return report.clinical_content

        patient = self.db.query(Patient).filter(Patient.id == report.patient_id).first()
        variants_data = self._variants_for_report(report, for_clinician=report.status == REPORT_STATUS_COMPLETED)
        content = rebuild_clinical_content_from_db(
            variants_data,
            report.drug_recommendations,
            patient_external_id=patient.external_id if patient else None,
        )
        if report.status != REPORT_STATUS_COMPLETED:
            return content

        report.clinical_content = content
        self.db.commit()
        self.db.refresh(report)
        return content

    def _variants_for_report(
        self,
        report: GenomicReport,
        *,
        for_clinician: bool = False,
    ) -> list[dict]:
        query = (
            self.db.query(Variant, VariantAnnotation)
            .join(VariantAnnotation, VariantAnnotation.variant_id == Variant.id)
            .join(SequencingSample, SequencingSample.id == Variant.sample_id)
            .filter(SequencingSample.patient_id == report.patient_id)
        )
        if report.pipeline_job_id:
            job = self.db.query(PipelineJob).filter(PipelineJob.id == report.pipeline_job_id).first()
            if job:
                query = query.filter(Variant.sample_id == job.sample_id)

        rows = query.all()
        result = []
        for v, ann in rows:
            if for_clinician and ann.requires_genetic_review and ann.review_status == "rejected":
                continue
            result.append(
                {
                    "chromosome": v.chromosome,
                    "position": v.position,
                    "ref_allele": v.ref_allele,
                    "alt_allele": v.alt_allele,
                    "variant_type": v.variant_type,
                    "quality_score": v.quality_score,
                    "depth": v.depth,
                    "rs_id": v.rs_id,
                    "gene": ann.gene,
                    "consequence": ann.consequence,
                    "annotation": {
                        "gene": ann.gene,
                        "consequence": ann.consequence,
                        "clinical_significance": ann.clinical_significance,
                        "pharmacogenomic_effect": ann.pharmacogenomic_effect,
                        "priority_score": ann.priority_score,
                        "ml_score": ann.ml_score,
                        "ml_confidence": ann.ml_confidence,
                        "interpretation": ann.interpretation,
                        "review_status": ann.review_status,
                        "requires_genetic_review": ann.requires_genetic_review,
                    },
                }
            )
        return result

    def list_all(self, skip: int = 0, limit: int = 50) -> list[GenomicReport]:
        return (
            self.db.query(GenomicReport)
            .order_by(GenomicReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_for_user(
        self,
        user_id: uuid.UUID,
        role: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[GenomicReport]:
        query = self.db.query(GenomicReport)
        if role == Role.CLINICIAN.value:
            query = query.join(Patient).filter(
                Patient.assigned_clinician_id == user_id,
                GenomicReport.status == REPORT_STATUS_COMPLETED,
            )
        elif not is_privileged_role(role):
            query = query.join(Patient).filter(Patient.assigned_clinician_id == user_id)
        return query.order_by(GenomicReport.created_at.desc()).offset(skip).limit(limit).all()

    def approve_report(
        self,
        report_id: uuid.UUID,
        approver_id: uuid.UUID,
        clinician_notes: str | None = None,
    ) -> GenomicReport | None:
        report = self.get_report(report_id)
        if not report:
            return None
        if report.status != REPORT_STATUS_PENDING_FINAL:
            return None
        if self.review.pending_variant_count(report_id) > 0:
            return None

        content = self.get_clinical_content(report, refresh=True)
        signature = compute_report_signature(str(report.id), content, str(approver_id))
        content["digital_signature"] = {
            "signature": signature,
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "approver_id": str(approver_id),
        }
        report.clinical_content = content
        report.status = REPORT_STATUS_COMPLETED
        report.approved_by = approver_id
        report.approved_at = datetime.now(timezone.utc)
        report.finalized_at = datetime.now(timezone.utc)
        if clinician_notes:
            report.clinician_notes = clinician_notes
        self.db.commit()
        self.db.refresh(report)
        return report

    def generate_pdf(self, report_id: uuid.UUID) -> bytes:
        report = self.get_report(report_id)
        if not report:
            raise ValueError("گزارش یافت نشد")

        patient = self.db.query(Patient).filter(Patient.id == report.patient_id).first()
        content = self.get_clinical_content(report, refresh=report.status == REPORT_STATUS_COMPLETED)
        approver = None
        if report.approved_by:
            approver = self.db.query(User).filter(User.id == report.approved_by).first()

        digital_sig = None
        if content.get("digital_signature"):
            digital_sig = content["digital_signature"].get("signature")

        return generate_clinical_pdf(
            report_id=str(report.id),
            patient_external_id=patient.external_id if patient else str(report.patient_id)[:8],
            clinical_content=content,
            report_status=report.status,
            created_at=report.created_at,
            approved_at=report.approved_at,
            approver_name=approver.full_name if approver else None,
            digital_signature=digital_sig,
        )

    def list_by_patient(self, patient_id: uuid.UUID, role: str | None = None) -> list[GenomicReport]:
        query = self.db.query(GenomicReport).filter(GenomicReport.patient_id == patient_id)
        if role == Role.CLINICIAN.value:
            query = query.filter(GenomicReport.status == REPORT_STATUS_COMPLETED)
        return query.order_by(GenomicReport.created_at.desc()).all()

    def get_patient_variants(
        self,
        patient_id: uuid.UUID,
        *,
        role: str | None = None,
    ) -> list[VariantWithAnnotation]:
        samples = self.db.query(SequencingSample).filter(SequencingSample.patient_id == patient_id).all()
        sample_ids = [s.id for s in samples]
        variants = self.db.query(Variant).filter(Variant.sample_id.in_(sample_ids)).all()

        result = []
        for v in variants:
            annotations = (
                self.db.query(VariantAnnotation).filter(VariantAnnotation.variant_id == v.id).all()
            )
            if role == Role.CLINICIAN.value:
                annotations = [
                    a for a in annotations if self.review.clinician_may_view_variant(a, patient_id)
                ]
            if not annotations:
                continue
            result.append(
                VariantWithAnnotation(
                    id=v.id,
                    chromosome=v.chromosome,
                    position=v.position,
                    ref_allele=v.ref_allele,
                    alt_allele=v.alt_allele,
                    variant_type=v.variant_type,
                    quality_score=v.quality_score,
                    rs_id=v.rs_id,
                    annotations=[VariantAnnotationResponse.model_validate(a) for a in annotations],
                )
            )
        return result

    def export_for_ehr(self, patient_id: uuid.UUID) -> EHRVariantExport | None:
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None

        variants = self.get_patient_variants(patient_id, role=Role.CLINICIAN.value)
        latest_report = (
            self.db.query(GenomicReport)
            .filter(GenomicReport.patient_id == patient_id, GenomicReport.status == REPORT_STATUS_COMPLETED)
            .order_by(GenomicReport.created_at.desc())
            .first()
        )

        clinical = None
        if latest_report:
            clinical = self.get_clinical_content(latest_report)

        return EHRVariantExport(
            patient_ehr_id=patient.ehr_patient_id or patient.external_id,
            report_id=latest_report.id if latest_report else None,
            issued_at=latest_report.finalized_at or latest_report.approved_at if latest_report else None,
            variants=variants,
            drug_recommendations=latest_report.drug_recommendations if latest_report else None,
            report_summary=latest_report.summary if latest_report else None,
            clinical_content=clinical,
        )
