"""add price_per_unit to discount_slabs

Revision ID: f8d2c4e6b1a3
Revises: e7a1b3c9f2d5
Create Date: 2026-04-07 22:30:00.000000

Additive only — adds a nullable column. Existing rows keep their
discount_percentage values and the app code falls back to percentage
when price_per_unit is NULL.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8d2c4e6b1a3'
down_revision = 'e7a1b3c9f2d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New column — flat price per unit in INR. Overrides percentage when set.
    op.add_column(
        'discount_slabs',
        sa.Column('price_per_unit', sa.Float(), nullable=True),
    )
    # Relax the existing discount_percentage column so it can be NULL for new slabs
    # that use flat pricing. Existing rows keep their values.
    op.alter_column(
        'discount_slabs',
        'discount_percentage',
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'discount_slabs',
        'discount_percentage',
        existing_type=sa.Float(),
        nullable=False,
    )
    op.drop_column('discount_slabs', 'price_per_unit')
