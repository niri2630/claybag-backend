from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(16), unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False)
    shipping_name = Column(String, nullable=False)
    shipping_phone = Column(String, nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_city = Column(String, nullable=False)
    shipping_pincode = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    cf_order_id = Column(String, nullable=True)  # Cashfree order ID
    payment_session_id = Column(String, nullable=True)  # Cashfree payment session
    payment_status = Column(String, nullable=True)  # Cashfree payment status
    coins_applied = Column(Float, default=0.0)
    referral_discount = Column(Float, default=0.0)
    # Promo code redemption — null for orders without a code
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True)
    coupon_discount = Column(Float, default=0.0, nullable=False)
    # GST breakdown (prices are inclusive — these are computed back from inclusive total)
    shipping_state = Column(String, nullable=True)         # Snapshotted for tax calc
    taxable_amount = Column(Float, nullable=True)          # Sum of (item_total / (1 + gst/100))
    cgst_amount = Column(Float, default=0.0)               # Intra-state only
    sgst_amount = Column(Float, default=0.0)               # Intra-state only
    igst_amount = Column(Float, default=0.0)               # Inter-state only
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tracking = relationship("OrderTracking", back_populates="order", cascade="all, delete-orphan")
    # post_update=True breaks the cycle with coupons.used_by_order_id ↔ orders.coupon_id
    coupon = relationship("Coupon", foreign_keys=[coupon_id], post_update=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    discount_applied = Column(Float, default=0.0)
    # GST snapshot (per line for invoice clarity)
    hsn_code = Column(String(10), nullable=True)
    gst_rate = Column(Float, nullable=True)  # Snapshot the rate used at order time
    # Per-area (formula pricing) fields — null for standard per-unit items
    dimension_length = Column(Float, nullable=True)   # Inches
    dimension_breadth = Column(Float, nullable=True)  # Inches
    computed_area = Column(Float, nullable=True)      # L x B x quantity (sq.in)
    area_rate = Column(Float, nullable=True)          # Rate per sq.in applied at order time

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    variant = relationship("ProductVariant", back_populates="order_items")


class OrderTracking(Base):
    __tablename__ = "order_tracking"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="tracking")
