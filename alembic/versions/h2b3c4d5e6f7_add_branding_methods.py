"""add branding_methods column to products

Revision ID: h2b3c4d5e6f7
Revises: g1a2b3c4d5e6
Create Date: 2026-04-14 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "h2b3c4d5e6f7"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("branding_methods", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "branding_methods")
