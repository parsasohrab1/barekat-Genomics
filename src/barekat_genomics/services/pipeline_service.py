"""سرویس اجرای پایپ‌لاین پردازش."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from barekat_genomics.core.config import get_settings
from barekat_genomics.core.review import (
    ML_REVIEW_THRESHOLD,
    REPORT_STATUS_PENDING_FINAL,
    REPORT_STATUS_PENDING_GENETIC,
    VARIANT_REVIEW_APPROVED,
    VARIANT_REVIEW_PENDING,
)
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.modules.registry import DEFAULT_MODULE, get_module
from barekat_genomics.pipeline.orchestrator import run_full_pipeline
from barekat_genomics.pipeline.priority import resolve_priority
from barekat_genomics.pipeline.runners import get_runner


STAGE_PROGRESS = {
    "queued": 5,
    "quality_control": 25,
    "variant_calling": 55,
    "interpretation": 80,
    "done": 100,
}

MODULE_REPORT_TYPE = {
    "pharmacogenomics": "pharmacogenomic",
    "pgx_panel": "pharmacogenomic",
    "cgp": "cancer_genomics",
    "carrier_screening": "carrier_screening",
    "tumor_normal": "tumor_normal",
    "prs": "polygenic_risk",
}


def compute_job_progress(job: PipelineJob) -> int:
    if job.status == "completed":
        return 100
    if job.status == "failed":
        return STAGE_PROGRESS.get(job.stage, 10)
    return STAGE_PROGRESS.get(job.stage, 5)


class PipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start_pipeline(
        self,
        sample_id: uuid.UUID,
        async_mode: bool = True,
        *,
        priority: str | None = None,
        backend: str | None = None,
        module: str | None = None,
        paired_sample_id: uuid.UUID | None = None,
    ) -> PipelineJob:
        sample = self.db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
        if not sample:
            raise ValueError(f"نمونه یافت نشد: {sample_id}")

        module_id = module or DEFAULT_MODULE
        mod = get_module(module_id)
        if mod.requires_paired_sample and not paired_sample_id:
            raise ValueError(f"ماژول {mod.name_fa} نیاز به نمونه جفت (paired_sample_id) دارد")
        if paired_sample_id:
            paired = self.db.query(SequencingSample).filter(SequencingSample.id == paired_sample_id).first()
            if not paired:
                raise ValueError(f"نمونه جفت یافت نشد: {paired_sample_id}")

        settings = get_settings()
        job_priority = resolve_priority(priority or sample.priority)
        job_backend = backend or settings.pipeline_backend

        job = PipelineJob(
            sample_id=sample_id,
            paired_sample_id=paired_sample_id,
            module=module_id,
            stage="queued",
            status="pending",
            priority=job_priority,
            backend=job_backend,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        if async_mode:
            runner = get_runner(job_backend)
            external_id = runner.submit(job, sample)
            if job_backend == "celery":
                job.celery_task_id = external_id
            else:
                job.external_job_id = external_id
            self.db.commit()
        else:
            self._execute_pipeline(job, sample)

        return job

    def _execute_pipeline(self, job: PipelineJob, sample: SequencingSample) -> None:
        from barekat_genomics.core.observability.metrics import (
            record_pipeline_error,
            record_qc_result,
            track_pipeline,
        )
        from barekat_genomics.core.observability.sentry_setup import capture_exception
        import structlog

        log = structlog.get_logger(__name__)

        with track_pipeline(job.priority, job.backend) as outcome:
            job.status = "running"
            job.stage = "quality_control"
            job.started_at = datetime.now(timezone.utc)
            self.db.commit()

            try:
                normal_interpretations = None
                if job.module == "tumor_normal" and job.paired_sample_id:
                    normal_sample = (
                        self.db.query(SequencingSample)
                        .filter(SequencingSample.id == job.paired_sample_id)
                        .first()
                    )
                    if normal_sample:
                        normal_result = run_full_pipeline(
                            normal_sample.storage_path,
                            normal_sample.file_type,
                            normal_sample.genome_build,
                            sample_label=normal_sample.sample_id,
                            module_id="pharmacogenomics",
                        )
                        if normal_result.success:
                            normal_interpretations = normal_result.interpretations

                result = run_full_pipeline(
                    sample.storage_path,
                    sample.file_type,
                    sample.genome_build,
                    sample_label=sample.sample_id,
                    module_id=job.module,
                    normal_interpretations=normal_interpretations,
                )
            except Exception as exc:
                log.exception("pipeline_execution_failed", job_id=str(job.id))
                capture_exception(exc, job_id=str(job.id), sample_id=str(sample.id))
                record_pipeline_error(job.stage, error_type=type(exc).__name__)
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                outcome["status"] = "failed"
                return

            job.qc_metrics = {
                "total_reads": result.qc_metrics.total_reads,
                "mean_quality": result.qc_metrics.mean_quality,
                "gc_content": result.qc_metrics.gc_content,
                "duplication_rate": result.qc_metrics.duplication_rate,
                "passed": result.qc_metrics.passed,
                "warnings": result.qc_metrics.warnings,
            }
            record_qc_result(result.qc_metrics.passed)

            if not result.success:
                error_type = "qc_failed" if not result.qc_metrics.passed else "pipeline_error"
                record_pipeline_error(job.stage, error_type=error_type)
                if result.error:
                    log.warning(
                        "pipeline_failed",
                        job_id=str(job.id),
                        error=result.error,
                        qc_passed=result.qc_metrics.passed,
                    )
                job.status = "failed"
                job.error_message = result.error
                job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                outcome["status"] = "failed"
                return

            job.stage = "variant_calling"
            self.db.commit()

            needs_genetic_review = False
            for called, interp in result.interpretations:
                requires_review = interp.ml_score > ML_REVIEW_THRESHOLD
                if requires_review:
                    needs_genetic_review = True

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
                    ml_score=interp.ml_score,
                    ml_confidence=interp.ml_confidence,
                    interpretation=interp.interpretation,
                    requires_genetic_review=requires_review,
                    review_status=VARIANT_REVIEW_PENDING if requires_review else VARIANT_REVIEW_APPROVED,
                )
                self.db.add(annotation)

            job.stage = "interpretation"
            self.db.commit()

            report_status = (
                REPORT_STATUS_PENDING_GENETIC if needs_genetic_review else REPORT_STATUS_PENDING_FINAL
            )
            report = GenomicReport(
                patient_id=sample.patient_id,
                pipeline_job_id=job.id,
                report_type=MODULE_REPORT_TYPE.get(job.module, "pharmacogenomic"),
                status=report_status,
                summary=result.report_summary,
                drug_recommendations=result.drug_recommendations,
                clinical_content=result.clinical_content,
                variant_summary={
                    "total_variants": len(result.variants),
                    "high_priority": sum(
                        1 for _, i in result.interpretations if i.ml_score > ML_REVIEW_THRESHOLD
                    ),
                    "pending_genetic_review": sum(
                        1 for _, i in result.interpretations if i.ml_score > ML_REVIEW_THRESHOLD
                    ),
                    "module": job.module,
                    "module_actionable": (result.module_analysis or {}).get("actionable_count", 0),
                },
            )
            self.db.add(report)

            sample.status = "processed"
            job.status = "completed"
            job.stage = "done"
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            outcome["status"] = "completed"
            outcome["variant_count"] = len(result.variants)

    def get_job(self, job_id: uuid.UUID) -> PipelineJob | None:
        return self.db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
