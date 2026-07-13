"""بررسی واریانت‌های با ML score بالا توسط ژنتیک‌دان."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from barekat_genomics.core.review import (
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_PENDING_FINAL,
    REPORT_STATUS_PENDING_GENETIC,
    VARIANT_REVIEW_APPROVED,
    VARIANT_REVIEW_PENDING,
    VARIANT_REVIEW_REJECTED,
)
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_review_queue(self, skip: int = 0, limit: int = 50) -> list[GenomicReport]:
        return (
            self.db.query(GenomicReport)
            .filter(GenomicReport.status == REPORT_STATUS_PENDING_GENETIC)
            .order_by(GenomicReport.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_pending_variants(self, report_id: uuid.UUID) -> list[tuple[Variant, VariantAnnotation]]:
        report = self.db.query(GenomicReport).filter(GenomicReport.id == report_id).first()
        if not report:
            return []
        query = (
            self.db.query(Variant, VariantAnnotation)
            .join(VariantAnnotation, VariantAnnotation.variant_id == Variant.id)
            .join(SequencingSample, SequencingSample.id == Variant.sample_id)
            .filter(
                SequencingSample.patient_id == report.patient_id,
                VariantAnnotation.requires_genetic_review.is_(True),
            )
        )
        if report.pipeline_job_id:
            job = self.db.query(PipelineJob).filter(PipelineJob.id == report.pipeline_job_id).first()
            if job:
                query = query.filter(Variant.sample_id == job.sample_id)
        return query.all()

    def review_variant(
        self,
        report_id: uuid.UUID,
        annotation_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        action: str,
        notes: str | None = None,
    ) -> VariantAnnotation | None:
        if action not in (VARIANT_REVIEW_APPROVED, VARIANT_REVIEW_REJECTED):
            return None
        report = self.db.query(GenomicReport).filter(GenomicReport.id == report_id).first()
        if not report or report.status != REPORT_STATUS_PENDING_GENETIC:
            return None

        pending = {ann.id: ann for _, ann in self.get_pending_variants(report_id)}
        ann = pending.get(annotation_id)
        if not ann or ann.review_status != VARIANT_REVIEW_PENDING:
            return None

        ann.review_status = action
        ann.reviewed_by = reviewer_id
        ann.reviewed_at = datetime.now(timezone.utc)
        ann.review_notes = notes
        self.db.commit()
        self.db.refresh(ann)

        if self.all_variants_reviewed(report_id):
            report.status = REPORT_STATUS_PENDING_FINAL
            self.db.commit()
        return ann

    def all_variants_reviewed(self, report_id: uuid.UUID) -> bool:
        rows = self.get_pending_variants(report_id)
        return all(ann.review_status != VARIANT_REVIEW_PENDING for _, ann in rows)

    def pending_variant_count(self, report_id: uuid.UUID) -> int:
        rows = self.get_pending_variants(report_id)
        return sum(1 for _, ann in rows if ann.review_status == VARIANT_REVIEW_PENDING)

    def clinician_may_view_report(self, report: GenomicReport) -> bool:
        return report.status == REPORT_STATUS_COMPLETED

    def clinician_may_view_variant(self, ann: VariantAnnotation, patient_id: uuid.UUID) -> bool:
        if not ann.requires_genetic_review:
            return True
        if ann.review_status != VARIANT_REVIEW_APPROVED:
            return False
        latest = (
            self.db.query(GenomicReport)
            .filter(GenomicReport.patient_id == patient_id)
            .order_by(GenomicReport.created_at.desc())
            .first()
        )
        return latest is not None and latest.status == REPORT_STATUS_COMPLETED
