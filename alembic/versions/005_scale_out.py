"""scale-out fields: sample priority, job backend, annotation cache

Revision ID: 005
Revises: 004
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sequencing_samples",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
    )
    op.create_index("ix_sequencing_samples_priority", "sequencing_samples", ["priority"])

    op.add_column(
        "pipeline_jobs",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
    )
    op.add_column(
        "pipeline_jobs",
        sa.Column("backend", sa.String(length=30), nullable=False, server_default="celery"),
    )
    op.add_column("pipeline_jobs", sa.Column("external_job_id", sa.String(length=200), nullable=True))
    op.add_column("pipeline_jobs", sa.Column("celery_queue", sa.String(length=50), nullable=True))
    op.create_index("ix_pipeline_jobs_priority", "pipeline_jobs", ["priority"])

    op.create_table(
        "annotation_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(200), nullable=False),
        sa.Column("rs_id", sa.String(50), nullable=True),
        sa.Column("genome_build", sa.String(20), nullable=False, server_default="GRCh38"),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("annotation_data", postgresql.JSON(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cache_key", name="uq_annotation_cache_key"),
    )
    op.create_index("ix_annotation_cache_cache_key", "annotation_cache", ["cache_key"])
    op.create_index("ix_annotation_cache_rs_id", "annotation_cache", ["rs_id"])

    op.alter_column("sequencing_samples", "priority", server_default=None)
    op.alter_column("pipeline_jobs", "priority", server_default=None)
    op.alter_column("pipeline_jobs", "backend", server_default=None)


def downgrade() -> None:
    op.drop_table("annotation_cache")
    op.drop_index("ix_pipeline_jobs_priority", "pipeline_jobs")
    op.drop_column("pipeline_jobs", "celery_queue")
    op.drop_column("pipeline_jobs", "external_job_id")
    op.drop_column("pipeline_jobs", "backend")
    op.drop_column("pipeline_jobs", "priority")
    op.drop_index("ix_sequencing_samples_priority", "sequencing_samples")
    op.drop_column("sequencing_samples", "priority")
