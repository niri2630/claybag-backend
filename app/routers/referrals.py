import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List

from app.database import get_db
from app.models.referral import ReferralCode, Referral
from app.models.wallet import Wallet, WalletTransaction
from app.models.user import User
from app.schemas.referral import ReferralCodeOut, ReferralOut, ReferralStatsOut, ApplyCodeRequest
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/referrals", tags=["referrals"])

REFERRAL_REWARD = 50.0  # Clay Coins


def _generate_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "CB" + "".join(secrets.choice(chars) for _ in range(6))


@router.get("/my-code", response_model=ReferralCodeOut)
def get_my_referral_code(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    rc = db.query(ReferralCode).filter(ReferralCode.user_id == current_user.id).first()
    if rc:
        return rc
    for _ in range(20):
        code = _generate_code()
        if not db.query(ReferralCode).filter(ReferralCode.code == code).first():
            rc = ReferralCode(user_id=current_user.id, code=code)
            db.add(rc)
            db.commit()
            db.refresh(rc)
            return rc
    raise HTTPException(500, "Could not generate unique referral code")


@router.get("/my-stats", response_model=ReferralStatsOut)
def get_my_referral_stats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    referrals = db.query(Referral).filter(Referral.referrer_id == current_user.id).all()
    total = len(referrals)
    completed = sum(1 for r in referrals if r.status == "completed")
    pending = sum(1 for r in referrals if r.status == "pending")
    total_earned = completed * REFERRAL_REWARD
    return ReferralStatsOut(
        total_referrals=total,
        completed_referrals=completed,
        total_earned=total_earned,
        pending=pending,
    )


@router.get("/my-history", response_model=List[ReferralOut])
def get_my_referral_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    referrals = db.query(Referral).filter(Referral.referrer_id == current_user.id).order_by(Referral.created_at.desc()).all()
    result = []
    for r in referrals:
        referred_user = db.query(User).filter(User.id == r.referred_id).first()
        out = ReferralOut.model_validate(r)
        out.referred_name = referred_user.name if referred_user else None
        out.referred_email = referred_user.email if referred_user else None
        result.append(out)
    return result


@router.post("/apply-code")
def apply_referral_code(data: ApplyCodeRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    code = data.code.strip().upper()
    rc = db.query(ReferralCode).filter(ReferralCode.code == code).first()
    if not rc:
        raise HTTPException(404, "Invalid referral code")
    if rc.user_id == current_user.id:
        raise HTTPException(400, "Cannot use your own referral code")
    existing = db.query(Referral).filter(Referral.referred_id == current_user.id).first()
    if existing:
        raise HTTPException(400, "You have already been referred")
    referral = Referral(
        referrer_id=rc.user_id,
        referred_id=current_user.id,
        referral_code=code,
        status="pending",
    )
    current_user.referred_by = code
    db.add(referral)
    db.commit()
    return {"message": "Referral code applied! You'll get 10% off your first order."}


@router.get("/my-discount-status")
def get_referral_discount_status(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if current user is eligible for 10% referral discount on first order."""
    if not current_user.referred_by:
        return {"eligible": False, "discount_percent": 0}
    referral = db.query(Referral).filter(
        Referral.referred_id == current_user.id,
        Referral.discount_used == False,
    ).first()
    if not referral:
        return {"eligible": False, "discount_percent": 0}
    from app.models.order import Order
    existing_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
    if existing_orders > 0:
        return {"eligible": False, "discount_percent": 0}
    return {"eligible": True, "discount_percent": 10}


def process_referral_rewards(order, db: Session):
    """Called after first order is confirmed. Credits referrer with Clay Coins."""
    user = db.query(User).filter(User.id == order.user_id).first()
    if not user or not user.referred_by:
        return

    # Lock the referral row to prevent double-crediting from concurrent webhook + verify
    referral = db.query(Referral).filter(Referral.referred_id == user.id).with_for_update().first()
    if not referral or referral.coins_credited:
        return

    # Credit referrer wallet (with row lock)
    from app.routers.wallet import get_or_create_wallet
    wallet = get_or_create_wallet(referral.referrer_id, db, lock=True)
    wallet.balance += REFERRAL_REWARD
    db.add(WalletTransaction(
        wallet_id=wallet.id,
        amount=REFERRAL_REWARD,
        type="CREDIT",
        source="REFERRAL",
        description=f"Referral reward: {user.name} placed their first order",
        reference_id=str(referral.id),
    ))
    referral.coins_credited = True
    referral.status = "completed"
    referral.completed_at = func.now()
    db.commit()


# --- Admin endpoints ---

@router.get("/all")
def list_all_referrals(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    referrals = db.query(Referral).order_by(Referral.created_at.desc()).all()
    result = []
    for r in referrals:
        referrer = db.query(User).filter(User.id == r.referrer_id).first()
        referred = db.query(User).filter(User.id == r.referred_id).first()
        result.append({
            "id": r.id,
            "referrer_name": referrer.name if referrer else None,
            "referrer_email": referrer.email if referrer else None,
            "referred_name": referred.name if referred else None,
            "referred_email": referred.email if referred else None,
            "referral_code": r.referral_code,
            "status": r.status,
            "coins_credited": r.coins_credited,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return result
