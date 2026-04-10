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
    # Use raw SQL with IF EXISTS/IF NOT EXISTS to handle production state
    # (some columns/constraints may already exist from manual hotfixes)
    conn = op.get_bind()

    # Clean up product_images variant FK (may have been added manually with different name)
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_product_images_variant_id"))
    # Drop old named FK if it exists
    conn.execute(sa.text("""
        DO $$ BEGIN
            ALTER TABLE product_images DROP CONSTRAINT IF EXISTS fk_product_images_variant;
        EXCEPTION WHEN OTHERS THEN NULL;
        END $$;
    """))

    # Ensure variant_id column exists on product_images (may already be there)
    conn.execute(sa.text("""
        ALTER TABLE product_images ADD COLUMN IF NOT EXISTS variant_id INTEGER REFERENCES product_variants(id);
    """))

    # Add new product columns
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS min_order_qty INTEGER"))
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS branding_info TEXT"))
    conn.execute(sa.text("ALTER TABLE products ADD COLUMN IF NOT EXISTS size_chart_url VARCHAR"))


def downgrade() -> None:
    op.drop_column('products', 'size_chart_url')
    op.drop_column('products', 'branding_info')
    op.drop_column('products', 'min_order_qty')
