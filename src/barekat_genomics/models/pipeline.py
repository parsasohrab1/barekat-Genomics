"""مدل وظایف پایپ‌لاین پردازش."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from barekat_genomics.core.database import Base


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequencing_samples.id"), nullable=False, index=True
    )
    paired_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequencing_samples.id"), nullable=True
    )
    module: Mapped[str] = mapped_column(String(50), default="pharmacogenomics", index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    backend: Mapped[str] = mapped_column(String(30), default="celery")
    external_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    celery_queue: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    qc_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sample: Mapped["SequencingSample"] = relationship(
        back_populates="pipeline_jobs",
        foreign_keys=[sample_id],
    )
    paired_sample: Mapped["SequencingSample | None"] = relationship(
        foreign_keys=[paired_sample_id],
    )


from barekat_genomics.models.sample import SequencingSample  # noqa: E402
