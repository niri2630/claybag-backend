"""add coupons table + order coupon columns

Revision ID: r2l3m4n5o6p7
Revises: q1k2l3m4n5o6
Create Date: 2026-05-02 14:00:00.000000

Adds the promo code system. Idempotent — safe to re-run.
"""
from alembic import op
import sqlalchemy as sa


revision = "r2l3m4n5o6p7"
down_revision = "q1k2l3m4n5o6"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :n"),
        {"n": name},
    ).first() is not None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first() is not None


def upgrade() -> None:
    if not _has_table("coupons"):
        op.create_table(
            "coupons",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("discount_type", sa.String(16), nullable=False),
            sa.Column("discount_value", sa.Float(), nullable=False),
            sa.Column("min_order_amount", sa.Float(), nullable=True),
            sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_by_order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    if not _has_column("orders", "coupon_id"):
        op.add_column(
            "orders",
            sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True),
        )
    if not _has_column("orders", "coupon_discount"):
        op.add_column("orders", sa.Column("coupon_discount", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    if _has_column("orders", "coupon_discount"):
        op.drop_column("orders", "coupon_discount")
    if _has_column("orders", "coupon_id"):
        op.drop_column("orders", "coupon_id")
    if _has_table("coupons"):
        op.drop_table("coupons")
