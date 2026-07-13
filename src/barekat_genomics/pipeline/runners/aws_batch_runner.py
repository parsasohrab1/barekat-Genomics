"""اجرای پایپ‌لاین روی AWS Batch."""

from __future__ import annotations

import json

from barekat_genomics.core.config import get_settings
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.pipeline.priority import resolve_celery_queue
from barekat_genomics.pipeline.runners.base import PipelineRunner


class AwsBatchRunner(PipelineRunner):
    name = "aws_batch"

    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        settings = get_settings()
        if not settings.aws_batch_job_queue or not settings.aws_batch_job_definition:
            raise RuntimeError("AWS Batch پیکربندی نشده — AWS_BATCH_JOB_QUEUE و AWS_BATCH_JOB_DEFINITION")

        import boto3

        batch = boto3.client("batch", region_name=settings.aws_region)
        queue_prio = resolve_celery_queue(job.priority)

        response = batch.submit_job(
            jobName=f"barekat-{str(job.id)[:8]}",
            jobQueue=settings.aws_batch_job_queue,
            jobDefinition=settings.aws_batch_job_definition,
            parameters={
                "job_id": str(job.id),
                "sample_id": str(sample.id),
                "storage_path": sample.storage_path,
                "file_type": sample.file_type,
                "genome_build": sample.genome_build,
            },
            containerOverrides={
                "environment": [
                    {"name": "PIPELINE_JOB_ID", "value": str(job.id)},
                    {"name": "CELERY_PRIORITY_QUEUE", "value": queue_prio},
                ],
            },
            tags={"priority": job.priority, "barekat-job-id": str(job.id)},
        )
        return response.get("jobId")
