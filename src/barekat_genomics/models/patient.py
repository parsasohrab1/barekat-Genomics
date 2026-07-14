"""مدل بیمار و داده‌های فنوتیپی."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from barekat_genomics.core.database import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_patient_org_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    encrypted_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ehr_patient_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    assigned_clinician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    samples: Mapped[list["SequencingSample"]] = relationship(back_populates="patient")
    reports: Mapped[list["GenomicReport"]] = relationship(back_populates="patient")


from barekat_genomics.models.report import GenomicReport  # noqa: E402
from barekat_genomics.models.sample import SequencingSample  # noqa: E402
