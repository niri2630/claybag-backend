"""add_variant_id_to_product_image

Revision ID: c5f3b2a1d9e8
Revises: b4e2a1c9d8f0
Create Date: 2026-04-07 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c5f3b2a1d9e8'
down_revision = 'b4e2a1c9d8f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('product_images', sa.Column('variant_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_product_images_variant',
        'product_images', 'product_variants',
        ['variant_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_product_images_variant_id', 'product_images', ['variant_id'])


def downgrade() -> None:
    op.drop_index('ix_product_images_variant_id', table_name='product_images')
    op.drop_constraint('fk_product_images_variant', 'product_images', type_='foreignkey')
    op.drop_column('product_images', 'variant_id')
