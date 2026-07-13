"""مدل گزارش تفسیر ژنومی."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from barekat_genomics.core.database import Base


class GenomicReport(Base):
    __tablename__ = "genomic_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True
    )
    pipeline_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_jobs.id"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(50), default="pharmacogenomic")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    drug_recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clinical_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    variant_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clinician_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="reports")


from barekat_genomics.models.patient import Patient  # noqa: E402
