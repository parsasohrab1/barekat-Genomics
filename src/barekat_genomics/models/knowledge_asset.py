"""ثبت دارایی دانشی / مالکیت فکری (مدل، روش، کیت نرم‌افزاری)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from barekat_genomics.core.database import Base


class KnowledgeAsset(Base):
    __tablename__ = "knowledge_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    asset_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_fa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # model | method | software_kit | dataset | guideline
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    inventors: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclosure_status: Mapped[str] = mapped_column(
        String(40), default="internal"
    )  # internal|disclosed|filed|granted|licensed
    patent_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    license: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_artifact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # e.g. variant_classifier_v2.pkl / assay:wes / module:pgx
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
