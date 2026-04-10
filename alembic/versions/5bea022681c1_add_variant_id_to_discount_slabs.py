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
    try:
        op.add_column('discount_slabs', sa.Column('variant_id', sa.Integer(), nullable=True))
    except Exception:
        pass
    try:
        op.create_foreign_key(None, 'discount_slabs', 'product_variants', ['variant_id'], ['id'], ondelete='SET NULL')
    except Exception:
        pass


def downgrade() -> None:
    op.drop_constraint(None, 'discount_slabs', type_='foreignkey')
    op.drop_column('discount_slabs', 'variant_id')
