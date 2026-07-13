"""genetic review fields on variant annotations

Revision ID: 004
Revises: 003
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("variant_annotations", sa.Column("ml_score", sa.Float(), nullable=True))
    op.add_column(
        "variant_annotations",
        sa.Column("requires_genetic_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("variant_annotations", sa.Column("review_status", sa.String(length=20), nullable=True))
    op.add_column(
        "variant_annotations",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_variant_annotations_reviewed_by_users",
        "variant_annotations",
        "users",
        ["reviewed_by"],
        ["id"],
    )
    op.add_column(
        "variant_annotations",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("variant_annotations", sa.Column("review_notes", sa.Text(), nullable=True))
    op.alter_column("variant_annotations", "requires_genetic_review", server_default=None)


def downgrade() -> None:
    op.drop_column("variant_annotations", "review_notes")
    op.drop_column("variant_annotations", "reviewed_at")
    op.drop_constraint("fk_variant_annotations_reviewed_by_users", "variant_annotations", type_="foreignkey")
    op.drop_column("variant_annotations", "reviewed_by")
    op.drop_column("variant_annotations", "review_status")
    op.drop_column("variant_annotations", "requires_genetic_review")
    op.drop_column("variant_annotations", "ml_score")
