"""RBAC fields: assigned clinician, report approval

Revision ID: 002
Revises: 001
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("assigned_clinician_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_patients_assigned_clinician",
        "patients",
        "users",
        ["assigned_clinician_id"],
        ["id"],
    )
    op.create_index("ix_patients_assigned_clinician_id", "patients", ["assigned_clinician_id"])

    op.add_column(
        "genomic_reports",
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "genomic_reports",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_genomic_reports_approved_by",
        "genomic_reports",
        "users",
        ["approved_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_genomic_reports_approved_by", "genomic_reports", type_="foreignkey")
    op.drop_column("genomic_reports", "approved_at")
    op.drop_column("genomic_reports", "approved_by")

    op.drop_index("ix_patients_assigned_clinician_id", table_name="patients")
    op.drop_constraint("fk_patients_assigned_clinician", "patients", type_="foreignkey")
    op.drop_column("patients", "assigned_clinician_id")
