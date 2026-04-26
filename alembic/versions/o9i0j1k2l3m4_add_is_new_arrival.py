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
    # Add column (idempotent)
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
    # Backfill: flag the 30 newest active products as new arrivals so the
    # public /new-arrivals page keeps showing the same products it was showing
    # under the date-based fallback. Admin can untoggle any of these later.
    op.execute("""
        UPDATE products
           SET is_new_arrival = TRUE
         WHERE id IN (
             SELECT id FROM products
              WHERE is_active = TRUE
              ORDER BY created_at DESC NULLS LAST, id DESC
              LIMIT 30
         );
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS is_new_arrival")
