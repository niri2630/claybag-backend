"""add company_profiles table

Revision ID: g1a2b3c4d5e6
Revises: 5bea022681c1
Create Date: 2026-04-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "g1a2b3c4d5e6"
down_revision = "5bea022681c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS company_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            company_name VARCHAR NOT NULL,
            business_type VARCHAR NOT NULL,
            gst_number VARCHAR,
            registered_address TEXT,
            contact_person VARCHAR,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_company_profiles_user_id ON company_profiles (user_id)")


def downgrade() -> None:
    op.drop_table("company_profiles")
