from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator


DiscountType = Literal["percent", "flat"]
CouponStatus = Literal["active", "scheduled", "expired", "used", "exhausted", "disabled"]


class CouponCreate(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: float
    min_order_amount: Optional[float] = None
    valid_from: datetime
    valid_until: datetime
    # Optional caps — any combination, all default null
    usage_limit: Optional[int] = None
    usage_limit_per_user: Optional[int] = None
    first_n_orders_only: Optional[int] = None
    # Empty list -> coupon is open to anyone with the code.
    # Non-empty -> only listed users can redeem.
    assigned_user_ids: List[int] = []

    @field_validator("usage_limit", "usage_limit_per_user", "first_n_orders_only")
    @classmethod
    def _v_pos(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v < 1:
            raise ValueError("Cap must be >= 1")
        return int(v)

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
    # null -> leave assignments unchanged. [] -> clear all. [1,2] -> replace.
    assigned_user_ids: Optional[List[int]] = None


class CouponAssigneeOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_value: float
    min_order_amount: Optional[float] = None
    valid_from: datetime
    valid_until: datetime
    is_active: bool
    usage_limit: Optional[int] = None
    usage_limit_per_user: Optional[int] = None
    first_n_orders_only: Optional[int] = None
    usage_count: int = 0
    used_at: Optional[datetime] = None
    used_by_order_id: Optional[int] = None
    created_at: datetime
    status: CouponStatus
    assigned_user_ids: List[int] = []
    assigned_users: List[CouponAssigneeOut] = []

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
