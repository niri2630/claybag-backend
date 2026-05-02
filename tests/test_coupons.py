"""Pure-logic tests for app/core/coupons.py.

These tests have no DB dependency — they exercise pricing math + status
derivation only.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.coupons import compute_discount, derive_status, is_exhausted, normalise_code, per_user_eligibility


def _coupon(**kw):
    """Build a coupon-like object with sane defaults (uses SimpleNamespace so
    tests don't depend on SQLAlchemy)."""
    now = datetime.now(timezone.utc)
    base = dict(
        discount_type="flat",
        discount_value=100.0,
        min_order_amount=None,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=1),
        is_active=True,
        used_at=None,
        usage_limit=None,
        usage_limit_per_user=None,
        first_n_orders_only=None,
        usage_count=0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


# ── normalise_code ──────────────────────────────────────────────────────────

def test_normalise_uppercases_and_strips():
    assert normalise_code(" client-acme ") == "CLIENT-ACME"


def test_normalise_blank_raises():
    with pytest.raises(ValueError):
        normalise_code("   ")


# ── compute_discount ────────────────────────────────────────────────────────

def test_compute_flat_discount_under_subtotal():
    c = _coupon(discount_type="flat", discount_value=200)
    assert compute_discount(c, subtotal=1000) == 200


def test_compute_flat_discount_clamps_to_subtotal():
    c = _coupon(discount_type="flat", discount_value=2000)
    assert compute_discount(c, subtotal=500) == 500


def test_compute_percent_discount():
    c = _coupon(discount_type="percent", discount_value=15)
    assert compute_discount(c, subtotal=1000) == 150.0


def test_compute_percent_rounds_to_2_decimals():
    c = _coupon(discount_type="percent", discount_value=10)
    assert compute_discount(c, subtotal=1234.56) == 123.46


def test_compute_returns_zero_when_below_min_order():
    c = _coupon(discount_type="flat", discount_value=200, min_order_amount=1000)
    assert compute_discount(c, subtotal=999.99) == 0


def test_compute_applies_at_exact_min_order():
    c = _coupon(discount_type="flat", discount_value=200, min_order_amount=1000)
    assert compute_discount(c, subtotal=1000) == 200


# ── derive_status ───────────────────────────────────────────────────────────

def test_status_active_within_window():
    assert derive_status(_coupon()) == "active"


def test_status_used_when_redeemed():
    c = _coupon(used_at=datetime.now(timezone.utc))
    assert derive_status(c) == "used"


def test_status_disabled_when_inactive():
    assert derive_status(_coupon(is_active=False)) == "disabled"


def test_status_scheduled_when_in_future():
    now = datetime.now(timezone.utc)
    c = _coupon(valid_from=now + timedelta(hours=1), valid_until=now + timedelta(hours=2))
    assert derive_status(c) == "scheduled"


def test_status_expired_when_past():
    now = datetime.now(timezone.utc)
    c = _coupon(valid_from=now - timedelta(hours=2), valid_until=now - timedelta(hours=1))
    assert derive_status(c) == "expired"


def test_status_used_takes_precedence_over_expired():
    now = datetime.now(timezone.utc)
    c = _coupon(
        used_at=now - timedelta(minutes=30),
        valid_from=now - timedelta(hours=2),
        valid_until=now - timedelta(hours=1),
    )
    assert derive_status(c) == "used"


# ── usage caps: is_exhausted + status ───────────────────────────────────────

def test_is_exhausted_legacy_one_time_via_used_at():
    c = _coupon(used_at=datetime.now(timezone.utc), usage_limit=None)
    assert is_exhausted(c) is True


def test_is_exhausted_cap_based_under_limit():
    c = _coupon(usage_limit=5, usage_count=3)
    assert is_exhausted(c) is False


def test_is_exhausted_cap_based_at_limit():
    c = _coupon(usage_limit=5, usage_count=5)
    assert is_exhausted(c) is True


def test_status_exhausted_when_cap_reached():
    c = _coupon(usage_limit=10, usage_count=10)
    assert derive_status(c) == "exhausted"


def test_status_active_when_cap_set_but_not_reached():
    c = _coupon(usage_limit=10, usage_count=3)
    assert derive_status(c) == "active"


# ── per_user_eligibility ────────────────────────────────────────────────────

def test_per_user_no_caps_passes():
    c = _coupon()
    assert per_user_eligibility(c, user_redemption_count=5, user_order_count=10) is None


def test_per_user_blocks_when_user_cap_reached():
    c = _coupon(usage_limit_per_user=2)
    assert per_user_eligibility(c, user_redemption_count=2, user_order_count=0) is not None


def test_per_user_passes_when_under_user_cap():
    c = _coupon(usage_limit_per_user=2)
    assert per_user_eligibility(c, user_redemption_count=1, user_order_count=0) is None


def test_first_n_orders_blocks_when_count_reached():
    c = _coupon(first_n_orders_only=3)
    assert per_user_eligibility(c, user_redemption_count=0, user_order_count=3) is not None


def test_first_n_orders_passes_under_threshold():
    c = _coupon(first_n_orders_only=3)
    assert per_user_eligibility(c, user_redemption_count=0, user_order_count=2) is None


def test_first_n_orders_passes_at_zero():
    c = _coupon(first_n_orders_only=3)
    assert per_user_eligibility(c, user_redemption_count=0, user_order_count=0) is None
