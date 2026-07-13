"""ثبت runnerهای پایپ‌لاین."""

from barekat_genomics.pipeline.runners.base import PipelineRunner


def get_runner(backend: str) -> PipelineRunner:
    from barekat_genomics.pipeline.runners.aws_batch_runner import AwsBatchRunner
    from barekat_genomics.pipeline.runners.celery_runner import CeleryRunner
    from barekat_genomics.pipeline.runners.kubernetes_runner import KubernetesRunner
    from barekat_genomics.pipeline.runners.nextflow_runner import NextflowRunner

    runners: dict[str, PipelineRunner] = {
        "celery": CeleryRunner(),
        "nextflow": NextflowRunner(),
        "kubernetes": KubernetesRunner(),
        "aws_batch": AwsBatchRunner(),
    }
    runner = runners.get(backend)
    if not runner:
        raise ValueError(f"بک‌اند پایپ‌لاین ناشناخته: {backend}")
    return runner
