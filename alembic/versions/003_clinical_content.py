"""clinical_content column for structured clinician reports

Revision ID: 003
Revises: 002
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "genomic_reports",
        sa.Column("clinical_content", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("genomic_reports", "clinical_content")
