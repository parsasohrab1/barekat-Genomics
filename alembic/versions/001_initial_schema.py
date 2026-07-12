"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(100), unique=True, nullable=False),
        sa.Column("encrypted_name", sa.Text(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("ehr_patient_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_patients_external_id", "patients", ["external_id"])
    op.create_index("ix_patients_ehr_patient_id", "patients", ["ehr_patient_id"])

    op.create_table(
        "sequencing_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("sample_id", sa.String(100), unique=True, nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), default="uploaded"),
        sa.Column("genome_build", sa.String(20), default="GRCh38"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "pipeline_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequencing_samples.id"), nullable=False),
        sa.Column("celery_task_id", sa.String(100), nullable=True),
        sa.Column("stage", sa.String(50), default="queued"),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("qc_metrics", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequencing_samples.id"), nullable=False),
        sa.Column("chromosome", sa.String(10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ref_allele", sa.String(500), nullable=False),
        sa.Column("alt_allele", sa.String(500), nullable=False),
        sa.Column("variant_type", sa.String(20), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("rs_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "variant_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("variants.id"), nullable=False),
        sa.Column("gene", sa.String(50), nullable=True),
        sa.Column("consequence", sa.String(100), nullable=True),
        sa.Column("clinical_significance", sa.String(50), nullable=True),
        sa.Column("pharmacogenomic_effect", sa.Text(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("ml_confidence", sa.Float(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "genomic_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("pipeline_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipeline_jobs.id"), nullable=True),
        sa.Column("report_type", sa.String(50), default="pharmacogenomic"),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("drug_recommendations", postgresql.JSON(), nullable=True),
        sa.Column("variant_summary", postgresql.JSON(), nullable=True),
        sa.Column("clinician_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("genomic_reports")
    op.drop_table("variant_annotations")
    op.drop_table("variants")
    op.drop_table("pipeline_jobs")
    op.drop_table("sequencing_samples")
    op.drop_table("patients")
    op.drop_table("users")
