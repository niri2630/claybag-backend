"""coupon usage caps + redemptions table

Revision ID: s3m4n5o6p7q8
Revises: r2l3m4n5o6p7
Create Date: 2026-05-02 22:00:00.000000

Three optional caps per coupon — admin can set any combination:
  • usage_limit          → global cap on total redemptions
  • usage_limit_per_user → max times same customer can redeem
  • first_n_orders_only  → only valid for customer's first N orders

Plus usage_count for tracking. New coupon_redemptions table audits each redemption
(needed for per-user check). Idempotent — safe to re-run.
"""
from alembic import op
import sqlalchemy as sa


revision = "s3m4n5o6p7q8"
down_revision = "r2l3m4n5o6p7"
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
    if not _has_column("coupons", "usage_limit"):
        op.add_column("coupons", sa.Column("usage_limit", sa.Integer(), nullable=True))
    if not _has_column("coupons", "usage_limit_per_user"):
        op.add_column("coupons", sa.Column("usage_limit_per_user", sa.Integer(), nullable=True))
    if not _has_column("coupons", "first_n_orders_only"):
        op.add_column("coupons", sa.Column("first_n_orders_only", sa.Integer(), nullable=True))
    if not _has_column("coupons", "usage_count"):
        op.add_column("coupons", sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"))

    if not _has_table("coupon_redemptions"):
        op.create_table(
            "coupon_redemptions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("redeemed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Backfill: any coupon already marked "used" via the legacy used_at field counts
    # as 1 redemption — keeps the global usage_count accurate.
    op.execute("""
        UPDATE coupons SET usage_count = 1
         WHERE used_at IS NOT NULL AND usage_count = 0;
    """)
    op.execute("""
        INSERT INTO coupon_redemptions (coupon_id, order_id, redeemed_at)
        SELECT c.id, c.used_by_order_id, c.used_at
          FROM coupons c
         WHERE c.used_at IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM coupon_redemptions r WHERE r.coupon_id = c.id
           );
    """)


def downgrade() -> None:
    if _has_table("coupon_redemptions"):
        op.drop_table("coupon_redemptions")
    for col in ("usage_count", "first_n_orders_only", "usage_limit_per_user", "usage_limit"):
        if _has_column("coupons", col):
            op.drop_column("coupons", col)
