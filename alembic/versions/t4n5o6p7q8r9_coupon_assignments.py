"""Coupon -> users assignment table.

Lets admin restrict a coupon to specific customers. Empty assignment list
means the coupon is open to anyone with the code (legacy behaviour).

Revision ID: t4n5o6p7q8r9
Revises: s3m4n5o6p7q8
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa


revision = "t4n5o6p7q8r9"
down_revision = "s3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "coupon_assignments" in insp.get_table_names():
        return

    op.create_table(
        "coupon_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "coupon_id",
            sa.Integer(),
            sa.ForeignKey("coupons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("coupon_id", "user_id", name="uq_coupon_user"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "coupon_assignments" in insp.get_table_names():
        op.drop_table("coupon_assignments")
