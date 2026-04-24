"""add moq_unit + pricing_mode on products, dimension fields on order_items

Revision ID: m7g8h9i0j1k2
Revises: l6f7g8h9i0j1
Create Date: 2026-04-24 12:00:00.000000

Adds:
  products.moq_unit VARCHAR DEFAULT 'pcs'
  products.pricing_mode VARCHAR DEFAULT 'per_unit'  (values: per_unit, per_area)
  order_items.dimension_length DOUBLE PRECISION NULL
  order_items.dimension_breadth DOUBLE PRECISION NULL
  order_items.computed_area DOUBLE PRECISION NULL
  order_items.area_rate DOUBLE PRECISION NULL
"""
from alembic import op


revision = "m7g8h9i0j1k2"
down_revision = "l6f7g8h9i0j1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'moq_unit'
            ) THEN
                ALTER TABLE products ADD COLUMN moq_unit VARCHAR DEFAULT 'pcs';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'pricing_mode'
            ) THEN
                ALTER TABLE products ADD COLUMN pricing_mode VARCHAR DEFAULT 'per_unit';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'dimension_length'
            ) THEN
                ALTER TABLE order_items ADD COLUMN dimension_length DOUBLE PRECISION;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'dimension_breadth'
            ) THEN
                ALTER TABLE order_items ADD COLUMN dimension_breadth DOUBLE PRECISION;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'computed_area'
            ) THEN
                ALTER TABLE order_items ADD COLUMN computed_area DOUBLE PRECISION;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'area_rate'
            ) THEN
                ALTER TABLE order_items ADD COLUMN area_rate DOUBLE PRECISION;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS moq_unit")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS pricing_mode")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS dimension_length")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS dimension_breadth")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS computed_area")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS area_rate")
