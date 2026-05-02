"""Promo code endpoints.

POST   /coupons             — admin: create
GET    /coupons             — admin: list (with derived status)
PATCH  /coupons/{id}        — admin: toggle active / extend valid_until
DELETE /coupons/{id}        — admin: delete (only if never used)
POST   /coupons/validate    — public: dry-run apply, returns discount or error
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.coupons import compute_discount, derive_status, normalise_code
from app.database import get_db
from app.models.coupon import Coupon
from app.core.security import get_current_admin
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
    return {
        "id": c.id,
        "code": c.code,
        "discount_type": c.discount_type,
        "discount_value": c.discount_value,
        "min_order_amount": c.min_order_amount,
        "valid_from": c.valid_from,
        "valid_until": c.valid_until,
        "is_active": c.is_active,
        "used_at": c.used_at,
        "used_by_order_id": c.used_by_order_id,
        "created_at": c.created_at,
        "status": derive_status(c),
    }


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
        created_by_user_id=getattr(admin, "id", None),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("", response_model=List[CouponOut])
def list_coupons(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    rows = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return [_to_out(c) for c in rows]


@router.get("/public", response_model=List[CouponOut])
def list_public_coupons(db: Session = Depends(get_db)):
    """Public listing of currently-redeemable codes — shown on checkout so
    customers can pick one. Filters to ACTIVE status only (window open, not
    used, not disabled). Server-side validation still enforces all limits at
    apply/order time."""
    rows = db.query(Coupon).order_by(Coupon.valid_until.asc()).all()
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
def validate_coupon(payload: CouponValidateRequest, db: Session = Depends(get_db)):
    """Public dry-run. Generic error for any failure to avoid leaking info."""
    try:
        code = normalise_code(payload.code)
    except ValueError:
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    c = db.query(Coupon).filter(Coupon.code == code).first()
    if c is None or derive_status(c) != "active":
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    discount = compute_discount(c, payload.subtotal)
    if discount <= 0:
        return CouponValidateResponse(ok=False, error=GENERIC_INVALID)

    return CouponValidateResponse(
        ok=True,
        discount=discount,
        discount_type=c.discount_type,
        final=max(0.0, payload.subtotal - discount),
    )
