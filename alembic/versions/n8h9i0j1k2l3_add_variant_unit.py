"""add variant_unit on product_variants

Revision ID: n8h9i0j1k2l3
Revises: m7g8h9i0j1k2
Create Date: 2026-04-25 13:00:00.000000

Adds:
  product_variants.variant_unit VARCHAR — optional unit label
    (e.g. "sq.in" for sticker size variants, NULL for normal variants like "S", "Red")
"""
from alembic import op


revision = "n8h9i0j1k2l3"
down_revision = "m7g8h9i0j1k2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'product_variants' AND column_name = 'variant_unit'
            ) THEN
                ALTER TABLE product_variants ADD COLUMN variant_unit VARCHAR;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE product_variants DROP COLUMN IF EXISTS variant_unit")
