"""add compare_price column to products

Revision ID: i3c4d5e6f7g8
Revises: h2b3c4d5e6f7
Create Date: 2026-04-14 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "i3c4d5e6f7g8"
down_revision = "h2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'compare_price'
            ) THEN
                ALTER TABLE products ADD COLUMN compare_price DOUBLE PRECISION;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("products", "compare_price")
