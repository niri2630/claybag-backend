"""Pure pricing + status helpers for the promo code system.

Kept free of SQLAlchemy/db imports so it is trivially unit-testable. The router
and order layer call these with a Coupon model instance — duck-typed access via
attribute names (so SimpleNamespace also works in tests).
"""
from datetime import datetime, timezone
from typing import Literal


CouponStatus = Literal["active", "scheduled", "expired", "used", "disabled"]


def normalise_code(raw: str) -> str:
    """Trim and uppercase. Raise ValueError on empty input."""
    v = (raw or "").strip().upper()
    if not v:
        raise ValueError("Code is required")
    return v


def compute_discount(coupon, subtotal: float) -> float:
    """Return ₹ discount this coupon would knock off the given subtotal.

    Returns 0 if subtotal is below min_order_amount. Flat discounts are clamped
    to the subtotal so we never drive the order negative. Percent discounts are
    rounded to 2 decimal places (existing convention across the codebase).
    """
    if coupon.min_order_amount is not None and subtotal < coupon.min_order_amount:
        return 0.0
    if coupon.discount_type == "flat":
        return float(min(coupon.discount_value, subtotal))
    if coupon.discount_type == "percent":
        raw = subtotal * coupon.discount_value / 100.0
        return round(float(raw), 2)
    return 0.0


def derive_status(coupon) -> CouponStatus:
    """Compute the human-friendly status shown in the admin UI.

    Priority: used > disabled > scheduled > expired > active. Used wins even on
    expired/disabled coupons because once redeemed the code is permanently
    consumed.
    """
    if coupon.used_at is not None:
        return "used"
    if not coupon.is_active:
        return "disabled"
    now = datetime.now(timezone.utc)
    valid_from = _aware(coupon.valid_from)
    valid_until = _aware(coupon.valid_until)
    if now < valid_from:
        return "scheduled"
    if now > valid_until:
        return "expired"
    return "active"


def _aware(dt: datetime) -> datetime:
    """Treat a naive datetime as UTC so comparisons don't blow up."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
