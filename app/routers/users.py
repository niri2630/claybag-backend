from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from app.core.security import get_current_admin, get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    """Admin: permanently delete a user and all related data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    # Delete related data
    from app.models.wallet import Wallet, WalletTransaction
    from app.models.referral import ReferralCode, Referral
    from app.models.company_profile import CompanyProfile
    from app.models.address import Address
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet:
        db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet.id).delete()
        db.delete(wallet)
    db.query(ReferralCode).filter(ReferralCode.user_id == user_id).delete()
    db.query(Referral).filter((Referral.referrer_id == user_id) | (Referral.referred_id == user_id)).delete()
    db.query(CompanyProfile).filter(CompanyProfile.user_id == user_id).delete()
    db.query(Address).filter(Address.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}
