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
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'branding_methods'
            ) THEN
                ALTER TABLE products ADD COLUMN branding_methods TEXT;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("products", "branding_methods")
