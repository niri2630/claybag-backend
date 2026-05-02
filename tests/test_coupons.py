"""Pure-logic tests for app/core/coupons.py.

These tests have no DB dependency — they exercise pricing math + status
derivation only.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.coupons import compute_discount, derive_status, normalise_code


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
