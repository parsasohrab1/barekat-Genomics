"""اجرای پایپ‌لاین روی Kubernetes Job."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from barekat_genomics.core.config import get_settings
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.pipeline.priority import resolve_celery_queue
from barekat_genomics.pipeline.runners.base import PipelineRunner


class KubernetesRunner(PipelineRunner):
    name = "kubernetes"

    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        settings = get_settings()
        template_path = Path(settings.kubernetes_job_template)
        if not template_path.exists():
            raise FileNotFoundError(f"قالب K8s یافت نشد: {template_path}")

        template = template_path.read_text(encoding="utf-8")
        job_name = f"barekat-pipeline-{str(job.id)[:8]}"
        queue = resolve_celery_queue(job.priority)

        manifest = (
            template.replace("{{JOB_NAME}}", job_name)
            .replace("{{NAMESPACE}}", settings.kubernetes_namespace)
            .replace("{{JOB_ID}}", str(job.id))
            .replace("{{SAMPLE_ID}}", str(sample.id))
            .replace("{{STORAGE_PATH}}", sample.storage_path)
            .replace("{{FILE_TYPE}}", sample.file_type)
            .replace("{{GENOME_BUILD}}", sample.genome_build)
            .replace("{{PRIORITY}}", queue)
            .replace("{{IMAGE}}", settings.kubernetes_worker_image)
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(manifest)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", tmp_path, "-n", settings.kubernetes_namespace],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"kubectl apply failed: {result.stderr}")
            return job_name
        finally:
            Path(tmp_path).unlink(missing_ok=True)
