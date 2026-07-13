"""کش تفسیر واریانت — جلوگیری از annotate مجدد همان rsID."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from barekat_genomics.core.database import Base


class AnnotationCacheEntry(Base):
    __tablename__ = "annotation_cache"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_annotation_cache_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    rs_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    genome_build: Mapped[str] = mapped_column(String(20), nullable=False, default="GRCh38")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    annotation_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    hit_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
