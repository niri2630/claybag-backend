from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    discount_type = Column(String(16), nullable=False)  # "percent" | "flat"
    discount_value = Column(Float, nullable=False)
    min_order_amount = Column(Float, nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    # Usage caps — all optional; any combination can apply.
    usage_limit = Column(Integer, nullable=True)              # global cap on total redemptions
    usage_limit_per_user = Column(Integer, nullable=True)     # max redemptions per customer
    first_n_orders_only = Column(Integer, nullable=True)      # restrict to customer's first N orders
    usage_count = Column(Integer, nullable=False, default=0)  # tracked global redemption count
    # Legacy "last used" pointers — kept for back-compat; usage_count is canonical.
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    used_by_order = relationship("Order", foreign_keys=[used_by_order_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    redemptions = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")


class CouponRedemption(Base):
    """Audit row per redemption — used for per-user cap enforcement."""
    __tablename__ = "coupon_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    coupon = relationship("Coupon", back_populates="redemptions")
