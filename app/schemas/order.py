from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int]
    quantity: int
    unit_price: float
    total_price: float
    discount_applied: float

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
    shipping_pincode: str
    notes: Optional[str] = None
    items: List[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None


class OrderOut(BaseModel):
    id: int
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
    created_at: datetime
    items: List[OrderItemOut] = []
    tracking: List[OrderTrackingOut] = []

    class Config:
        from_attributes = True
