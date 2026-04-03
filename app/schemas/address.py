from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AddressCreate(BaseModel):
    label: str = "Home"
    name: str
    phone: str
    address: str
    city: str
    pincode: str
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    is_default: Optional[bool] = None


class AddressOut(BaseModel):
    id: int
    label: str
    name: str
    phone: str
    address: str
    city: str
    pincode: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True
