"""رابط اجرای پایپ‌لاین روی بک‌اند‌های مختلف."""

from __future__ import annotations

from abc import ABC, abstractmethod

from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.sample import SequencingSample


class PipelineRunner(ABC):
    name: str

    @abstractmethod
    def submit(self, job: PipelineJob, sample: SequencingSample) -> str | None:
        """شروع اجرا — برگرداندن external job id یا celery task id."""
