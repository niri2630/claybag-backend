"""add order_number to orders

Revision ID: e7a1b3c9f2d5
Revises: c5f3b2a1d9e8
Create Date: 2026-04-07 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import secrets


# revision identifiers, used by Alembic.
revision = 'e7a1b3c9f2d5'
down_revision = 'c5f3b2a1d9e8'
branch_labels = None
depends_on = None


_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _gen(length: int = 8) -> str:
    return "CB-" + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def upgrade() -> None:
    # Add the column as nullable first so existing rows don't blow up
    op.add_column('orders', sa.Column('order_number', sa.String(length=16), nullable=True))
    op.create_index('ix_orders_order_number', 'orders', ['order_number'], unique=True)

    # Backfill existing orders with unique random order_numbers
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT id FROM orders WHERE order_number IS NULL ORDER BY id"))
    existing_numbers = set()
    for row in result:
        order_id = row[0]
        # Generate until unique
        for _ in range(15):
            candidate = _gen(8)
            if candidate not in existing_numbers:
                existing_numbers.add(candidate)
                bind.execute(
                    sa.text("UPDATE orders SET order_number = :num WHERE id = :id"),
                    {"num": candidate, "id": order_id},
                )
                break


def downgrade() -> None:
    op.drop_index('ix_orders_order_number', table_name='orders')
    op.drop_column('orders', 'order_number')
