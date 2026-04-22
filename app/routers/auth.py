from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.referral import ReferralCode, Referral
from app.models.wallet import Wallet, WalletTransaction
from app.schemas.user import UserCreate, LoginRequest, Token, UserOut, ForgotPasswordRequest, ResetPasswordRequest
from app.core.security import hash_password, verify_password, create_access_token
from app.core.otp_store import generate_otp, verify_otp
from app.core.email import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])

SIGNUP_BONUS = 100.0  # Clay Coins credited to every new account


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
    )
    # Handle referral code if provided
    if data.referral_code:
        code = data.referral_code.strip().upper()
        rc = db.query(ReferralCode).filter(ReferralCode.code == code).first()
        if rc:
            user.referred_by = code
    db.add(user)
    db.commit()
    db.refresh(user)

    # Welcome bonus: credit SIGNUP_BONUS Clay Coins to the new user's wallet
    wallet = Wallet(user_id=user.id, balance=SIGNUP_BONUS)
    db.add(wallet)
    db.flush()  # get wallet.id without ending the transaction
    db.add(WalletTransaction(
        wallet_id=wallet.id,
        amount=SIGNUP_BONUS,
        type="CREDIT",
        source="SIGNUP",
        description="Welcome bonus for creating a ClayBag account",
        reference_id=None,
    ))
    db.commit()

    # Create referral record if referred
    if user.referred_by:
        rc = db.query(ReferralCode).filter(ReferralCode.code == user.referred_by).first()
        if rc:
            referral = Referral(
                referrer_id=rc.user_id,
                referred_id=user.id,
                referral_code=user.referred_by,
                status="pending",
            )
            db.add(referral)
            db.commit()
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always return same message to prevent email enumeration
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If an account exists with this email, an OTP has been sent."}
    otp = generate_otp(data.email)
    if otp is None:
        raise HTTPException(status_code=429, detail="Please wait before requesting another OTP.")
    send_otp_email(data.email, otp)
    return {"message": "If an account exists with this email, an OTP has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not verify_otp(data.email, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password cannot be the same as your current password")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password reset successful"}


@router.post("/admin-login", response_model=Token)
def admin_login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}
