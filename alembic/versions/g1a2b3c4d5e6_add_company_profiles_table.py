"""add company_profiles table

Revision ID: g1a2b3c4d5e6
Revises: f8d2c4e6b1a3
Create Date: 2026-04-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "g1a2b3c4d5e6"
down_revision = "f8d2c4e6b1a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True, index=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("business_type", sa.String(), nullable=False),
        sa.Column("gst_number", sa.String(), nullable=True),
        sa.Column("registered_address", sa.Text(), nullable=True),
        sa.Column("contact_person", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("company_profiles")
