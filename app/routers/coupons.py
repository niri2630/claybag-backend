"""Promo code endpoints.

POST   /coupons             — admin: create
GET    /coupons             — admin: list (with derived status)
PATCH  /coupons/{id}        — admin: toggle active / extend valid_until
DELETE /coupons/{id}        — admin: delete (only if never used)
POST   /coupons/validate    — public: dry-run apply, returns discount or error
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.coupons import (
    compute_discount,
    derive_status,
    normalise_code,
    per_user_eligibility,
)
from app.database import get_db
from app.models.coupon import Coupon, CouponAssignment, CouponRedemption
from app.models.order import Order
from app.models.user import User
from app.core.security import (
    get_current_admin,
    get_current_user,
    get_optional_current_user,
)
from app.schemas.coupon import (
    CouponCreate,
    CouponOut,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidateResponse,
)

router = APIRouter(prefix="/coupons", tags=["coupons"])


GENERIC_INVALID = "Invalid or expired code"


def _to_out(c: Coupon) -> dict:
    assignments = list(getattr(c, "assignments", []) or [])
    assigned_users = [
        {"id": a.user.id, "name": a.user.name, "email": a.user.email}
        for a in assignments
        if a.user is not None
    ]
    return {
        "id": c.id,
        "code": c.code,
        "discount_type": c.discount_type,
        "discount_value": c.discount_value,
        "min_order_amount": c.min_order_amount,
        "valid_from": c.valid_from,
        "valid_until": c.valid_until,
        "is_active": c.is_active,
        "usage_limit": c.usage_limit,
        "usage_limit_per_user": c.usage_limit_per_user,
        "first_n_orders_only": c.first_n_orders_only,
        "usage_count": c.usage_count or 0,
        "used_at": c.used_at,
        "used_by_order_id": c.used_by_order_id,
        "created_at": c.created_at,
        "status": derive_status(c),
        "assigned_user_ids": [a.user_id for a in assignments],
        "assigned_users": assigned_users,
    }


def _set_assignments(db: Session, coupon: Coupon, user_ids: List[int]) -> None:
    """Replace the coupon's assignment list with the given user_ids.

    Deduplicates and silently drops user_ids that don't resolve to existing
    users (defensive — admin UI always sends real ids).
    """
    unique_ids = list({int(uid) for uid in user_ids})
    valid_ids: List[int] = []
    if unique_ids:
        rows = db.query(User.id).filter(User.id.in_(unique_ids)).all()
        valid_ids = [r[0] for r in rows]

    # Drop existing
    db.query(CouponAssignment).filter(CouponAssignment.coupon_id == coupon.id).delete(
        synchronize_session=False
    )
    for uid in valid_ids:
        db.add(CouponAssignment(coupon_id=coupon.id, user_id=uid))


def _user_is_eligible(coupon: Coupon, user_id: Optional[int]) -> bool:
    """If the coupon has any assignments, user must be in the list."""
    assignments = list(getattr(coupon, "assignments", []) or [])
    if not assignments:
        return True
    if user_id is None:
        return False
    return any(a.user_id == user_id for a in assignments)


@router.post("", response_model=CouponOut)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if data.valid_until <= data.valid_from:
        raise HTTPException(400, "valid_until must be after valid_from")
    if data.discount_type == "percent" and data.discount_value > 100:
        raise HTTPException(400, "Percent discount cannot exceed 100")

    code = normalise_code(data.code)
    if db.query(Coupon).filter(Coupon.code == code).first():
        raise HTTPException(409, "This code already exists")

    c = Coupon(
        code=code,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        min_order_amount=data.min_order_amount,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        is_active=True,
        usage_limit=data.usage_limit,
        usage_limit_per_user=data.usage_limit_per_user,
        first_n_orders_only=data.first_n_orders_only,
        created_by_user_id=getattr(admin, "id", None),
    )
    db.add(c)
    db.flush()  # need c.id before inserting assignments
    if data.assigned_user_ids:
        _set_assignments(db, c, data.assigned_user_ids)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("", response_model=List[CouponOut])
def list_coupons(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    rows = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return [_to_out(c) for c in rows]


@router.get("/my", response_model=List[CouponOut])
def list_my_coupons(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Coupons currently available to the logged-in customer.

    Returns active coupons that are explicitly assigned to this user (via the
    coupon_assignments table). Open (unassigned) coupons are NOT listed here —
    those are private codes shared out-of-band and the customer is expected to
    type them at checkout.
    """
    rows = (
        db.query(Coupon)
        .join(CouponAssignment, CouponAssignment.coupon_id == Coupon.id)
        .filter(CouponAssignment.user_id == current_user.id)
        .order_by(Coupon.valid_until.asc())
        .all()
    )
    return [_to_out(c) for c in rows if derive_status(c) == "active"]


@router.patch("/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    c = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not c:
        raise HTTPException(404, "Coupon not found")
    if data.valid_until is not None:
        if data.valid_until <= c.valid_from:
            raise HTTPException(400, "valid_until must be after valid_from")
        c.valid_until = data.valid_until
    if data.is_active is not None:
        c.is_active = data.is_active
    if data.assigned_user_ids is not None:
        _set_assignments(db, c, data.assigned_user_ids)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{coupon_id}")
def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    c = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not c:
        raise HTTPException(404, "Coupon not found")
    if c.used_at is not None:
        raise HTTPException(409, "Cannot delete a coupon that has been redeemed")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/validate", response_model=CouponValidateResponse)
def validate_coupon(
    payload: CouponValidateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_current_user),
):
    """Public dry-run with optional auth.

    When the request carries a valid bearer token we run the per-user and
    first-N-orders caps as well, so logged-in customers get an immediate
    "code already redeemed" / "new customers only" error at apply time
    instead of waiting until checkout submission.
    """
    try:
        code = normalise_code(payload.code)
    except ValueError:
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    c = db.query(Coupon).filter(Coupon.code == code).first()
    if c is None or derive_status(c) != "active":
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    # User-pinned coupon: must be on the assignment list.
    user_id = getattr(current_user, "id", None)
    if not _user_is_eligible(c, user_id):
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    # Per-user / first-N caps (only when we have a user)
    if current_user is not None:
        user_redemptions = (
            db.query(CouponRedemption)
            .filter(
                CouponRedemption.coupon_id == c.id,
                CouponRedemption.user_id == current_user.id,
            )
            .count()
        )
        user_orders = (
            db.query(Order)
            .filter(Order.user_id == current_user.id)
            .count()
        )
        err = per_user_eligibility(c, user_redemptions, user_orders)
        if err is not None:
            return CouponValidateResponse(ok=False, error=err)

    discount = compute_discount(c, payload.subtotal)
    if discount <= 0:
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    return CouponValidateResponse(
        ok=True,
        discount=discount,
        discount_type=c.discount_type,
        final=max(0.0, payload.subtotal - discount),
    )
