"""وظایف Celery برای پایپ‌لاین."""

from barekat_genomics.tasks.celery_app import celery_app
from barekat_genomics.core.database import SessionLocal
from barekat_genomics.core.observability.sentry_setup import capture_exception, init_sentry
from barekat_genomics.services.pipeline_service import PipelineService

init_sentry()


@celery_app.task(name="barekat_genomics.run_pipeline", bind=True, max_retries=3)
def run_pipeline_task(self, job_id: str) -> dict:
    import uuid

    db = SessionLocal()
    try:
        service = PipelineService(db)
        job = service.get_job(uuid.UUID(job_id))
        if not job:
            return {"status": "error", "message": "Job not found"}

        from barekat_genomics.models.sample import SequencingSample
        sample = db.query(SequencingSample).filter(SequencingSample.id == job.sample_id).first()
        if not sample:
            return {"status": "error", "message": "Sample not found"}

        service._execute_pipeline(job, sample)
        db.refresh(job)
        return {"status": job.status, "job_id": job_id}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            capture_exception(exc, job_id=job_id, task="run_pipeline")
        self.retry(exc=exc, countdown=60)
    finally:
        db.close()
