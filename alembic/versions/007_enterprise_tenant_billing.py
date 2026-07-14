"""Enterprise multi-tenant + billing schema

Revision ID: 007
Revises: 006
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_fa", sa.String(255), nullable=True),
        sa.Column("deployment_mode", sa.String(20), server_default="saas"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("settings_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_fa", sa.String(100), nullable=True),
        sa.Column("deployment_mode", sa.String(20), server_default="saas"),
        sa.Column("price_monthly_usd", sa.Float(), server_default="0"),
        sa.Column("max_users", sa.Integer(), server_default="5"),
        sa.Column("max_samples_month", sa.Integer(), server_default="50"),
        sa.Column("max_storage_gb", sa.Integer(), server_default="100"),
        sa.Column("features_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.add_column(
        "users",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_organization_id",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.add_column(
        "patients",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_patients_organization_id",
        "patients",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index("ix_patients_organization_id", "patients", ["organization_id"])
    try:
        op.drop_constraint("patients_external_id_key", "patients", type_="unique")
    except Exception:
        pass
    try:
        op.drop_index("ix_patients_external_id", table_name="patients")
    except Exception:
        pass
    op.create_index("ix_patients_external_id", "patients", ["external_id"])
    op.create_unique_constraint(
        "uq_patient_org_external",
        "patients",
        ["organization_id", "external_id"],
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_role", sa.String(50), server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("billing_cycle", sa.String(20), server_default="monthly"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("samples_used_period", sa.Integer(), server_default="0"),
        sa.Column("seats_used", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id"),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("amount_usd", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("organization_memberships")
    op.drop_constraint("uq_patient_org_external", "patients", type_="unique")
    op.drop_constraint("fk_patients_organization_id", "patients", type_="foreignkey")
    op.drop_index("ix_patients_organization_id", table_name="patients")
    op.drop_column("patients", "organization_id")
    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_column("users", "organization_id")
    op.drop_table("plans")
    op.drop_table("organizations")
