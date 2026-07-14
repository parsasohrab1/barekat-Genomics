"""وظایف Celery برای پایپ‌لاین با retry هوشمند."""

from __future__ import annotations

import uuid

from barekat_genomics.core.database import SessionLocal
from barekat_genomics.core.observability.sentry_setup import capture_exception, init_sentry
from barekat_genomics.services.pipeline_service import PipelineService
from barekat_genomics.tasks.celery_app import celery_app

init_sentry()

# خطاهای موقتی قابل retry (IO / broker / شبکه)
_RETRYABLE_MARKERS = (
    "Timeout",
    "Connection",
    "Unavailable",
    "Temporary",
    "timed out",
    "Broken pipe",
    "Connection reset",
    "MinIO",
    "S3",
    "endpoint",
)


def _is_retryable(exc: BaseException) -> bool:
    msg = str(exc)
    return any(m.lower() in msg.lower() for m in _RETRYABLE_MARKERS)


@celery_app.task(
    name="barekat_genomics.run_pipeline",
    bind=True,
    max_retries=3,
    soft_time_limit=6 * 3600,
    time_limit=7 * 3600,
)
def run_pipeline_task(self, job_id: str) -> dict:
    db = SessionLocal()
    service = PipelineService(db)
    try:
        job = service.get_job(uuid.UUID(job_id))
        if not job:
            return {"status": "error", "message": "Job not found"}

        from barekat_genomics.models.sample import SequencingSample

        sample = db.query(SequencingSample).filter(SequencingSample.id == job.sample_id).first()
        if not sample:
            return {"status": "error", "message": "Sample not found"}

        service._execute_pipeline(job, sample)
        db.refresh(job)
        return {
            "status": job.status,
            "job_id": job_id,
            "stage": job.stage,
            "retries": self.request.retries,
        }
    except Exception as exc:
        try:
            job = service.get_job(uuid.UUID(job_id))
            if job and job.status not in ("completed", "failed"):
                if _is_retryable(exc) and self.request.retries < self.max_retries:
                    job.status = "pending"
                else:
                    job.status = "failed"
                job.error_message = str(exc)[:2000]
                db.commit()
        except Exception:
            pass

        if _is_retryable(exc) and self.request.retries < self.max_retries:
            countdown = 60 * (2**self.request.retries)
            raise self.retry(exc=exc, countdown=countdown) from exc

        capture_exception(exc, job_id=job_id, task="run_pipeline")
        raise
    finally:
        db.close()
