from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.wallet import Wallet, WalletTransaction
from app.schemas.wallet import WalletOut, WalletTransactionOut, AdminCreditRequest
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/wallet", tags=["wallet"])


def get_or_create_wallet(user_id: int, db: Session, lock: bool = False) -> Wallet:
    """Get or create wallet. Use lock=True when mutating balance."""
    q = db.query(Wallet).filter(Wallet.user_id == user_id)
    if lock:
        q = q.with_for_update()
    wallet = q.first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


@router.get("/me", response_model=WalletOut)
def get_my_wallet(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_create_wallet(current_user.id, db)


@router.get("/transactions", response_model=List[WalletTransactionOut])
def get_my_transactions(
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = get_or_create_wallet(current_user.id, db)
    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Admin endpoints ---

@router.get("/all")
def list_all_wallets(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    wallets = db.query(Wallet).all()
    from app.models.user import User
    result = []
    for w in wallets:
        user = db.query(User).filter(User.id == w.user_id).first()
        result.append({
            "id": w.id,
            "user_id": w.user_id,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
            "balance": w.balance,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })
    return result


@router.post("/credit/{user_id}")
def admin_credit_wallet(user_id: int, data: AdminCreditRequest, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    if data.amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    wallet = get_or_create_wallet(user_id, db, lock=True)
    wallet.balance += data.amount
    db.add(WalletTransaction(
        wallet_id=wallet.id,
        amount=data.amount,
        type="CREDIT",
        source="ADMIN",
        description=data.description,
    ))
    db.commit()
    db.refresh(wallet)
    return {"message": f"Credited {data.amount} Clay Coins", "balance": wallet.balance}
