"""سرویس اجرای پایپ‌لاین پردازش."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.pipeline.orchestrator import run_full_pipeline


class PipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start_pipeline(self, sample_id: uuid.UUID, async_mode: bool = True) -> PipelineJob:
        sample = self.db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
        if not sample:
            raise ValueError(f"نمونه یافت نشد: {sample_id}")

        job = PipelineJob(sample_id=sample_id, stage="queued", status="pending")
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        if async_mode:
            from barekat_genomics.tasks.pipeline_tasks import run_pipeline_task

            task = run_pipeline_task.delay(str(job.id))
            job.celery_task_id = task.id
            self.db.commit()
        else:
            self._execute_pipeline(job, sample)

        return job

    def _execute_pipeline(self, job: PipelineJob, sample: SequencingSample) -> None:
        job.status = "running"
        job.stage = "quality_control"
        job.started_at = datetime.now(timezone.utc)
        self.db.commit()

        result = run_full_pipeline(sample.storage_path, sample.file_type, sample.genome_build)

        job.qc_metrics = {
            "total_reads": result.qc_metrics.total_reads,
            "mean_quality": result.qc_metrics.mean_quality,
            "gc_content": result.qc_metrics.gc_content,
            "duplication_rate": result.qc_metrics.duplication_rate,
            "passed": result.qc_metrics.passed,
            "warnings": result.qc_metrics.warnings,
        }

        if not result.success:
            job.status = "failed"
            job.error_message = result.error
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return

        job.stage = "variant_calling"
        self.db.commit()

        for called, interp in result.interpretations:
            variant = Variant(
                sample_id=sample.id,
                chromosome=called.chromosome,
                position=called.position,
                ref_allele=called.ref_allele,
                alt_allele=called.alt_allele,
                variant_type=called.variant_type,
                quality_score=called.quality_score,
                depth=called.depth,
                rs_id=called.rs_id,
            )
            self.db.add(variant)
            self.db.flush()

            annotation = VariantAnnotation(
                variant_id=variant.id,
                gene=interp.gene,
                consequence=interp.consequence,
                clinical_significance=interp.clinical_significance,
                pharmacogenomic_effect=interp.pharmacogenomic_effect,
                priority_score=interp.priority_score,
                ml_confidence=interp.ml_confidence,
                interpretation=interp.interpretation,
            )
            self.db.add(annotation)

        job.stage = "interpretation"
        self.db.commit()

        report = GenomicReport(
            patient_id=sample.patient_id,
            pipeline_job_id=job.id,
            report_type="pharmacogenomic",
            status="completed",
            summary=result.report_summary,
            drug_recommendations=result.drug_recommendations,
            variant_summary={
                "total_variants": len(result.variants),
                "high_priority": sum(1 for _, i in result.interpretations if i.priority_score > 0.5),
            },
            finalized_at=datetime.now(timezone.utc),
        )
        self.db.add(report)

        sample.status = "processed"
        job.status = "completed"
        job.stage = "done"
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def get_job(self, job_id: uuid.UUID) -> PipelineJob | None:
        return self.db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
