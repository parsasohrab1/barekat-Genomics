"""کش نتایج پایپ‌لاین و هزینه محاسبات."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from barekat_genomics.core.database import Base


class PipelineResultCache(Base):
    __tablename__ = "pipeline_result_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    assay_type: Mapped[str] = mapped_column(String(20), default="panel")
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    genome_build: Mapped[str] = mapped_column(String(20), default="GRCh38")
    module_id: Mapped[str] = mapped_column(String(50), default="pgx")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComputeCostRecord(Base):
    __tablename__ = "compute_cost_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_jobs.id"), nullable=True, index=True
    )
    assay_type: Mapped[str] = mapped_column(String(20), default="panel")
    backend: Mapped[str] = mapped_column(String(30), default="celery")
    cpu_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
