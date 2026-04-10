"""add_moq_branding_sizechart

Revision ID: e261ff3092a4
Revises: f8d2c4e6b1a3
Create Date: 2026-04-10 14:04:44.208024

"""
from alembic import op
import sqlalchemy as sa


revision = 'e261ff3092a4'
down_revision = 'f8d2c4e6b1a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safe: only add columns if they don't exist (production may already have them from hotfixes)
    conn = op.get_bind()

    # Check if variant_id FK constraint needs cleanup (may have been added manually)
    try:
        op.drop_index('ix_product_images_variant_id', table_name='product_images')
    except Exception:
        pass  # index may not exist

    try:
        op.drop_constraint('fk_product_images_variant', 'product_images', type_='foreignkey')
    except Exception:
        pass  # constraint may not exist or have a different name

    # Ensure the FK exists with proper naming
    try:
        op.create_foreign_key(None, 'product_images', 'product_variants', ['variant_id'], ['id'])
    except Exception:
        pass  # FK may already exist

    # Add new product columns (safe: nullable, no default conflicts)
    for col_name, col_type in [('min_order_qty', sa.Integer()), ('branding_info', sa.Text()), ('size_chart_url', sa.String())]:
        try:
            op.add_column('products', sa.Column(col_name, col_type, nullable=True))
        except Exception:
            pass  # column may already exist


def downgrade() -> None:
    op.drop_column('products', 'size_chart_url')
    op.drop_column('products', 'branding_info')
    op.drop_column('products', 'min_order_qty')
