"""Pure pricing + status helpers for the promo code system.

Kept free of SQLAlchemy/db imports so it is trivially unit-testable. The router
and order layer call these with a Coupon model instance — duck-typed access via
attribute names (so SimpleNamespace also works in tests).
"""
from datetime import datetime, timezone
from typing import Literal, Optional


CouponStatus = Literal["active", "scheduled", "expired", "used", "exhausted", "disabled"]


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


def is_exhausted(coupon) -> bool:
    """True when the coupon's global usage_limit cap is reached.

    Legacy semantics: when usage_limit is null, the coupon is one-time-use; we
    derive exhaustion from the legacy used_at field instead. New coupons with
    usage_limit set use the count.
    """
    limit = getattr(coupon, "usage_limit", None)
    count = getattr(coupon, "usage_count", 0) or 0
    if limit is None:
        # Legacy / undefined cap: treat presence of used_at as exhausted (one-time).
        return getattr(coupon, "used_at", None) is not None
    return count >= limit


def derive_status(coupon) -> CouponStatus:
    """Compute the human-friendly status shown in the admin UI.

    Priority: exhausted/used > disabled > scheduled > expired > active.
    'exhausted' is the new state for cap-based coupons; 'used' is kept for the
    one-time legacy case so older coupons keep showing as expected in the UI.
    """
    if is_exhausted(coupon):
        # If a usage_limit is set we surface exhaustion explicitly; otherwise
        # the legacy "used" badge stays.
        if getattr(coupon, "usage_limit", None) is not None:
            return "exhausted"
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


def per_user_eligibility(coupon, user_redemption_count: int, user_order_count: int) -> Optional[str]:
    """Return None if the user can redeem this coupon; otherwise a generic
    error string. Pure function — caller supplies the counts queried from DB.

    Two checks:
      • usage_limit_per_user: this user has already redeemed >= cap
      • first_n_orders_only:  this user has placed >= cap orders already
    """
    per_user = getattr(coupon, "usage_limit_per_user", None)
    if per_user is not None and user_redemption_count >= per_user:
        return "Code already redeemed (per-customer limit reached)"
    first_n = getattr(coupon, "first_n_orders_only", None)
    if first_n is not None and user_order_count >= first_n:
        return "Code is for new customers only"
    return None


def _aware(dt: datetime) -> datetime:
    """Treat a naive datetime as UTC so comparisons don't blow up."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
