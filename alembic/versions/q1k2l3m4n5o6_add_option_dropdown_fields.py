"""add option_dropdown variant mode fields

Revision ID: q1k2l3m4n5o6
Revises: p0j1k2l3m4n5
Create Date: 2026-04-28 10:00:00.000000

Adds support for a new variant_mode "option_dropdown" used by products like
standees, photo frames, table-top displays where:
  - The customer picks ONE option from a dropdown (e.g. A3 / A4 / A5).
  - Each option has its own selling price + MRP (no base+adjustment).
  - A standard quantity selector + bulk slab applies on top.

Schema additions (all nullable, idempotent):
  • products.variant_mode_override  — per-product override of category mode
  • products.option_label           — admin-customisable dropdown header
  • product_variants.option_price   — full selling price for this option
  • product_variants.option_mrp     — full MRP for strikethrough
"""
from alembic import op
import sqlalchemy as sa


revision = "q1k2l3m4n5o6"
down_revision = "p0j1k2l3m4n5"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    res = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return res is not None


def upgrade() -> None:
    if not _has_column("products", "variant_mode_override"):
        op.add_column("products", sa.Column("variant_mode_override", sa.String(), nullable=True))
    if not _has_column("products", "option_label"):
        op.add_column("products", sa.Column("option_label", sa.String(), nullable=True))
    if not _has_column("product_variants", "option_price"):
        op.add_column("product_variants", sa.Column("option_price", sa.Float(), nullable=True))
    if not _has_column("product_variants", "option_mrp"):
        op.add_column("product_variants", sa.Column("option_mrp", sa.Float(), nullable=True))


def downgrade() -> None:
    if _has_column("product_variants", "option_mrp"):
        op.drop_column("product_variants", "option_mrp")
    if _has_column("product_variants", "option_price"):
        op.drop_column("product_variants", "option_price")
    if _has_column("products", "option_label"):
        op.drop_column("products", "option_label")
    if _has_column("products", "variant_mode_override"):
        op.drop_column("products", "variant_mode_override")
