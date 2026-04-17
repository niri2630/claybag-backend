from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ReferralCodeOut(BaseModel):
    code: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReferralOut(BaseModel):
    id: int
    referrer_id: int
    referred_id: int
    referred_name: Optional[str] = None
    referred_email: Optional[str] = None
    referral_code: str
    status: str
    discount_used: bool
    coins_credited: bool
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReferralStatsOut(BaseModel):
    total_referrals: int
    completed_referrals: int
    total_earned: float
    pending: int


class ApplyCodeRequest(BaseModel):
    code: str
