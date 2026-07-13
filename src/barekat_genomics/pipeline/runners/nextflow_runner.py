"""اجرای reproducible با Nextflow."""

from __future__ import annotations

import subprocess
from pathlib import Path

from barekat_genomics.core.config import get_settings
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.pipeline.runners.base import PipelineRunner


class NextflowRunner(PipelineRunner):
    name = "nextflow"

    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        settings = get_settings()
        workflow = Path(settings.nextflow_workflow_path)
        if not workflow.exists():
            raise FileNotFoundError(f"Nextflow workflow یافت نشد: {workflow}")

        outdir = Path(settings.pipeline_work_dir) / str(job.id)
        outdir.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.nextflow_executable,
            "run",
            str(workflow),
            "-profile",
            settings.nextflow_profile,
            "--input",
            sample.storage_path,
            "--file_type",
            sample.file_type,
            "--genome_build",
            sample.genome_build,
            "--job_id",
            str(job.id),
            "--outdir",
            str(outdir),
            "-with-report",
            str(outdir / "report.html"),
            "-resume",
        ]
        if settings.nextflow_executor:
            cmd.extend(["-executor", settings.nextflow_executor])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return f"nf-{job.id}-{proc.pid}"
