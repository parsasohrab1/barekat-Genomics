"""مدل واریانت‌های ژنومی."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from barekat_genomics.core.database import Base


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sequencing_samples.id"), nullable=False, index=True
    )
    chromosome: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ref_allele: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_allele: Mapped[str] = mapped_column(String(500), nullable=False)
    variant_type: Mapped[str] = mapped_column(String(20), nullable=False)  # SNP, INDEL
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rs_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sample: Mapped["SequencingSample"] = relationship(back_populates="variants")
    annotations: Mapped[list["VariantAnnotation"]] = relationship(back_populates="variant")


class VariantAnnotation(Base):
    __tablename__ = "variant_annotations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("variants.id"), nullable=False, index=True
    )
    gene: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    consequence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clinical_significance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pharmacogenomic_effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ml_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    variant: Mapped["Variant"] = relationship(back_populates="annotations")


from barekat_genomics.models.sample import SequencingSample  # noqa: E402
