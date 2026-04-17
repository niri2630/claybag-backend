"""add wallet and referral tables

Revision ID: j4d5e6f7g8h9
Revises: i3c4d5e6f7g8
Create Date: 2026-04-15 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "j4d5e6f7g8h9"
down_revision = "i3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            balance DOUBLE PRECISION NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wallets_user_id ON wallets (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id SERIAL PRIMARY KEY,
            wallet_id INTEGER NOT NULL REFERENCES wallets(id),
            amount DOUBLE PRECISION NOT NULL,
            type VARCHAR NOT NULL,
            source VARCHAR NOT NULL,
            description TEXT,
            reference_id VARCHAR,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wallet_transactions_wallet_id ON wallet_transactions (wallet_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS referral_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            code VARCHAR(12) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_referral_codes_code ON referral_codes (code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_referral_codes_user_id ON referral_codes (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer_id INTEGER NOT NULL REFERENCES users(id),
            referred_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            referral_code VARCHAR NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            discount_used BOOLEAN DEFAULT FALSE,
            coins_credited BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'referred_by'
            ) THEN
                ALTER TABLE users ADD COLUMN referred_by VARCHAR;
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'coins_applied'
            ) THEN
                ALTER TABLE orders ADD COLUMN coins_applied DOUBLE PRECISION DEFAULT 0;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'referral_discount'
            ) THEN
                ALTER TABLE orders ADD COLUMN referral_discount DOUBLE PRECISION DEFAULT 0;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("referrals")
    op.drop_table("referral_codes")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS referred_by")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS coins_applied")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS referral_discount")
