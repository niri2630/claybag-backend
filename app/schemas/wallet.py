from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WalletOut(BaseModel):
    id: int
    user_id: int
    balance: float
    created_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionOut(BaseModel):
    id: int
    amount: float
    type: str
    source: str
    description: Optional[str]
    reference_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AdminCreditRequest(BaseModel):
    amount: float
    description: str
