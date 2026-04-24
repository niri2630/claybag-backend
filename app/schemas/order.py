from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from app.models.order import OrderStatus

# Indian states + UTs (case/spacing-insensitive validation)
_INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "delhi", "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal",
    "andaman and nicobar islands", "chandigarh",
    "dadra and nagar haveli and daman and diu",
    "jammu and kashmir", "ladakh", "lakshadweep", "puducherry",
}


def _validate_state(v: Optional[str]) -> Optional[str]:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.lower() not in _INDIAN_STATES:
        raise ValueError(f"Invalid Indian state: {s}")
    return s


class OrderItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    # Per-area pricing (stickers etc.) — null for regular per-unit products
    dimension_length: Optional[float] = None   # Inches
    dimension_breadth: Optional[float] = None  # Inches


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    product_image: Optional[str] = None
    variant_id: Optional[int] = None
    variant_label: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float
    discount_applied: float
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    # Per-area line items (stickers) — null otherwise
    dimension_length: Optional[float] = None
    dimension_breadth: Optional[float] = None
    computed_area: Optional[float] = None
    area_rate: Optional[float] = None

    class Config:
        from_attributes = True


class OrderTrackingOut(BaseModel):
    id: int
    status: OrderStatus
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    shipping_state: Optional[str] = None
    shipping_pincode: str
    notes: Optional[str] = None
    coins_applied: Optional[float] = 0.0
    use_referral_discount: Optional[bool] = False
    items: List[OrderItemCreate]

    @field_validator("shipping_state")
    @classmethod
    def _v_state(cls, v): return _validate_state(v)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    order_number: Optional[str] = None
    user_id: int
    status: OrderStatus
    total_amount: float
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    shipping_pincode: str
    notes: Optional[str]
    cf_order_id: Optional[str] = None
    payment_status: Optional[str] = None
    coins_applied: Optional[float] = 0.0
    referral_discount: Optional[float] = 0.0
    shipping_state: Optional[str] = None
    taxable_amount: Optional[float] = None
    cgst_amount: Optional[float] = 0.0
    sgst_amount: Optional[float] = 0.0
    igst_amount: Optional[float] = 0.0
    created_at: datetime
    items: List[OrderItemOut] = []
    tracking: List[OrderTrackingOut] = []

    class Config:
        from_attributes = True
