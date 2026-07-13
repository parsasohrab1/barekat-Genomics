"""incremental diagnostic modules

Revision ID: 006
Revises: 005
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_jobs",
        sa.Column("module", sa.String(length=50), nullable=False, server_default="pharmacogenomics"),
    )
    op.add_column(
        "pipeline_jobs",
        sa.Column("paired_sample_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pipeline_jobs_paired_sample",
        "pipeline_jobs",
        "sequencing_samples",
        ["paired_sample_id"],
        ["id"],
    )
    op.create_index("ix_pipeline_jobs_module", "pipeline_jobs", ["module"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_jobs_module", table_name="pipeline_jobs")
    op.drop_constraint("fk_pipeline_jobs_paired_sample", "pipeline_jobs", type_="foreignkey")
    op.drop_column("pipeline_jobs", "paired_sample_id")
    op.drop_column("pipeline_jobs", "module")
