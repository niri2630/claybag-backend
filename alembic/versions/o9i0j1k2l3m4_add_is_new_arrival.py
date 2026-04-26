"""add is_new_arrival on products

Revision ID: o9i0j1k2l3m4
Revises: n8h9i0j1k2l3
Create Date: 2026-04-26 10:00:00.000000

Adds:
  products.is_new_arrival BOOLEAN NOT NULL DEFAULT FALSE
    — admin-curated flag to surface a product on the public /new-arrivals page.
"""
from alembic import op


revision = "o9i0j1k2l3m4"
down_revision = "n8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'is_new_arrival'
            ) THEN
                ALTER TABLE products
                  ADD COLUMN is_new_arrival BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS is_new_arrival")
