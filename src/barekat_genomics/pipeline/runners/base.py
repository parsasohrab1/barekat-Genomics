"""Interface for running the pipeline on different backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample


class PipelineRunner(ABC):
    name: str

    @abstractmethod
    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        """Start the run — return the external job id or celery task id."""
