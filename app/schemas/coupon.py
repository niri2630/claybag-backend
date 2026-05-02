from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


DiscountType = Literal["percent", "flat"]
CouponStatus = Literal["active", "scheduled", "expired", "used", "disabled"]


class CouponCreate(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: float
    min_order_amount: Optional[float] = None
    valid_from: datetime
    valid_until: datetime

    @field_validator("code")
    @classmethod
    def _v_code(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if not v:
            raise ValueError("Code is required")
        if len(v) > 64:
            raise ValueError("Code must be 64 characters or fewer")
        for ch in v:
            if not (ch.isalnum() or ch in ("-", "_")):
                raise ValueError("Code may only contain letters, digits, dash, underscore")
        return v

    @field_validator("discount_value")
    @classmethod
    def _v_value(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("discount_value must be > 0")
        return round(float(v), 2)

    @field_validator("min_order_amount")
    @classmethod
    def _v_min(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v < 0:
            raise ValueError("min_order_amount must be >= 0")
        return round(float(v), 2)


class CouponUpdate(BaseModel):
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_value: float
    min_order_amount: Optional[float] = None
    valid_from: datetime
    valid_until: datetime
    is_active: bool
    used_at: Optional[datetime] = None
    used_by_order_id: Optional[int] = None
    created_at: datetime
    status: CouponStatus

    class Config:
        from_attributes = True


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float

    @field_validator("subtotal")
    @classmethod
    def _v_sub(cls, v: float) -> float:
        if v < 0:
            raise ValueError("subtotal must be >= 0")
        return float(v)


class CouponValidateResponse(BaseModel):
    ok: bool
    discount: float = 0.0
    discount_type: Optional[DiscountType] = None
    final: float = 0.0
    error: Optional[str] = None
