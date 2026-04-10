"""add_variant_id_to_discount_slabs

Revision ID: 5bea022681c1
Revises: e261ff3092a4
Create Date: 2026-04-10 14:14:20.942340

"""
from alembic import op
import sqlalchemy as sa


revision = '5bea022681c1'
down_revision = 'e261ff3092a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE discount_slabs ADD COLUMN IF NOT EXISTS variant_id INTEGER
        REFERENCES product_variants(id) ON DELETE SET NULL
    """))


def downgrade() -> None:
    op.drop_column('discount_slabs', 'variant_id')
