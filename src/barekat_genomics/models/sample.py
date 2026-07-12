"""مدل نمونه توالی‌یابی (FASTQ/BAM)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from barekat_genomics.core.database import Base


class SequencingSample(Base):
    __tablename__ = "sequencing_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    sample_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # FASTQ, BAM
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    genome_build: Mapped[str] = mapped_column(String(20), default="GRCh38")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    patient: Mapped["Patient"] = relationship(back_populates="samples")
    pipeline_jobs: Mapped[list["PipelineJob"]] = relationship(back_populates="sample")
    variants: Mapped[list["Variant"]] = relationship(back_populates="sample")


from barekat_genomics.models.patient import Patient  # noqa: E402
from barekat_genomics.models.pipeline import PipelineJob  # noqa: E402
from barekat_genomics.models.variant import Variant  # noqa: E402
