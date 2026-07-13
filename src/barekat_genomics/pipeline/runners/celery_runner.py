"""اجرای پایپ‌لاین از طریق صف اولویت‌دار Celery."""

from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.pipeline.priority import resolve_celery_queue
from barekat_genomics.pipeline.runners.base import PipelineRunner


class CeleryRunner(PipelineRunner):
    name = "celery"

    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        from barekat_genomics.tasks.pipeline_tasks import run_pipeline_task

        queue = resolve_celery_queue(job.priority)
        job.celery_queue = queue
        task = run_pipeline_task.apply_async(args=[str(job.id)], queue=queue)
        return task.id
