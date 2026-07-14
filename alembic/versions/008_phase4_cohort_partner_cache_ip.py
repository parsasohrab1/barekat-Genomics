"""Phase 4 cohort, partner API, cache, IP assets, assay fields

Revision ID: 008
Revises: 007
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sequencing_samples", sa.Column("assay_type", sa.String(20), server_default="panel"))
    op.add_column("sequencing_samples", sa.Column("target_bed", sa.String(255), nullable=True))
    op.create_index("ix_sequencing_samples_assay_type", "sequencing_samples", ["assay_type"])

    op.create_table(
        "cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_fa", sa.String(255), nullable=True),
        sa.Column("population", sa.String(50), server_default="iranian"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_cohorts_code", "cohorts", ["code"])
    op.create_index("ix_cohorts_organization_id", "cohorts", ["organization_id"])

    op.create_table(
        "cohort_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cohorts.id"), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequencing_samples.id"), nullable=False),
        sa.Column("patient_external_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("cohort_id", "sample_id", name="uq_cohort_sample"),
    )

    op.create_table(
        "partner_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("scopes", sa.Text()),
        sa.Column("rate_limit_per_minute", sa.Integer(), server_default="60"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_partner_api_keys_key_hash", "partner_api_keys", ["key_hash"], unique=True)
    op.create_index("ix_partner_api_keys_key_prefix", "partner_api_keys", ["key_prefix"])

    op.create_table(
        "pipeline_result_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(128), nullable=False),
        sa.Column("assay_type", sa.String(20), server_default="panel"),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("genome_build", sa.String(20), server_default="GRCh38"),
        sa.Column("module_id", sa.String(50), server_default="pgx"),
        sa.Column("result_json", postgresql.JSON(), nullable=True),
        sa.Column("hit_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pipeline_result_cache_cache_key", "pipeline_result_cache", ["cache_key"], unique=True)

    op.create_table(
        "compute_cost_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipeline_jobs.id"), nullable=True),
        sa.Column("assay_type", sa.String(20), server_default="panel"),
        sa.Column("backend", sa.String(30), server_default="celery"),
        sa.Column("cpu_seconds", sa.Float(), server_default="0"),
        sa.Column("estimated_usd", sa.Float(), server_default="0"),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "knowledge_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("asset_code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("title_fa", sa.String(255), nullable=True),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), server_default="1.0"),
        sa.Column("inventors", sa.Text(), nullable=True),
        sa.Column("disclosure_status", sa.String(40), server_default="internal"),
        sa.Column("patent_ref", sa.String(120), nullable=True),
        sa.Column("license", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("linked_artifact", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_knowledge_assets_asset_code", "knowledge_assets", ["asset_code"], unique=True)


def downgrade() -> None:
    op.drop_table("knowledge_assets")
    op.drop_table("compute_cost_records")
    op.drop_table("pipeline_result_cache")
    op.drop_table("partner_api_keys")
    op.drop_table("cohort_members")
    op.drop_table("cohorts")
    op.drop_index("ix_sequencing_samples_assay_type", table_name="sequencing_samples")
    op.drop_column("sequencing_samples", "target_bed")
    op.drop_column("sequencing_samples", "assay_type")
