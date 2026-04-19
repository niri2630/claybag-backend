"""add hsn_code, gst_rate to products + GST breakdown to orders + state to addresses

Revision ID: l6f7g8h9i0j1
Revises: k5e6f7g8h9i0
Create Date: 2026-04-19 12:00:00.000000
"""
from alembic import op

revision = "l6f7g8h9i0j1"
down_revision = "k5e6f7g8h9i0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Products: HSN code + product-level GST rate override
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'hsn_code'
            ) THEN
                ALTER TABLE products ADD COLUMN hsn_code VARCHAR(10);
                CREATE INDEX IF NOT EXISTS ix_products_hsn_code ON products (hsn_code);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'gst_rate'
            ) THEN
                ALTER TABLE products ADD COLUMN gst_rate DOUBLE PRECISION;
            END IF;
        END $$;
    """)

    # Addresses: state (required for GST intra/inter detection)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'addresses' AND column_name = 'state'
            ) THEN
                ALTER TABLE addresses ADD COLUMN state VARCHAR;
            END IF;
        END $$;
    """)

    # Orders: GST breakdown columns
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'shipping_state'
            ) THEN
                ALTER TABLE orders ADD COLUMN shipping_state VARCHAR;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'taxable_amount'
            ) THEN
                ALTER TABLE orders ADD COLUMN taxable_amount DOUBLE PRECISION;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'cgst_amount'
            ) THEN
                ALTER TABLE orders ADD COLUMN cgst_amount DOUBLE PRECISION DEFAULT 0;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'sgst_amount'
            ) THEN
                ALTER TABLE orders ADD COLUMN sgst_amount DOUBLE PRECISION DEFAULT 0;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'igst_amount'
            ) THEN
                ALTER TABLE orders ADD COLUMN igst_amount DOUBLE PRECISION DEFAULT 0;
            END IF;
        END $$;
    """)

    # Order items: HSN + GST snapshot
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'hsn_code'
            ) THEN
                ALTER TABLE order_items ADD COLUMN hsn_code VARCHAR(10);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'order_items' AND column_name = 'gst_rate'
            ) THEN
                ALTER TABLE order_items ADD COLUMN gst_rate DOUBLE PRECISION;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS gst_rate")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS hsn_code")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS igst_amount")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS sgst_amount")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS cgst_amount")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS taxable_amount")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS shipping_state")
    op.execute("ALTER TABLE addresses DROP COLUMN IF EXISTS state")
    op.execute("DROP INDEX IF EXISTS ix_products_hsn_code")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS gst_rate")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS hsn_code")
