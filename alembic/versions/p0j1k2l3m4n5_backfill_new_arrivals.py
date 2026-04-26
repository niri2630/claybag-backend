"""backfill is_new_arrival for the 30 newest active products

Revision ID: p0j1k2l3m4n5
Revises: o9i0j1k2l3m4
Create Date: 2026-04-26 11:00:00.000000

The previous migration added the is_new_arrival column with a FALSE default.
On deploys where the column was added before the backfill statement was
introduced, the public /new-arrivals page ends up nearly empty until the
admin manually flags products.

This migration is a safety-net backfill: only runs when fewer than 5
products are currently flagged, so a real curated list is never overwritten.
It marks the 30 newest active products as is_new_arrival = TRUE.
"""
from alembic import op


revision = "p0j1k2l3m4n5"
down_revision = "o9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            flagged_count integer;
        BEGIN
            SELECT COUNT(*) INTO flagged_count
              FROM products
             WHERE is_new_arrival = TRUE;

            IF flagged_count < 5 THEN
                UPDATE products
                   SET is_new_arrival = TRUE
                 WHERE id IN (
                     SELECT id FROM products
                      WHERE is_active = TRUE
                      ORDER BY created_at DESC NULLS LAST, id DESC
                      LIMIT 30
                 );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # No-op — backfill is idempotent and we never want to undo it.
    pass
