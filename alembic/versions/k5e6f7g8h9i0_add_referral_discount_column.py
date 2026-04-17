"""add referral_discount column to orders

Revision ID: k5e6f7g8h9i0
Revises: j4d5e6f7g8h9
Create Date: 2026-04-17 12:00:00.000000
"""
from alembic import op

revision = "k5e6f7g8h9i0"
down_revision = "j4d5e6f7g8h9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'referral_discount'
            ) THEN
                ALTER TABLE orders ADD COLUMN referral_discount DOUBLE PRECISION DEFAULT 0;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS referral_discount")
