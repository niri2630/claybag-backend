from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

# Same whitelist as orders schema
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


def _v_state(v: Optional[str]) -> Optional[str]:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.lower() not in _INDIAN_STATES:
        raise ValueError(f"Invalid Indian state: {s}")
    return s


class AddressCreate(BaseModel):
    label: str = "Home"
    name: str
    phone: str
    address: str
    city: str
    state: Optional[str] = None
    pincode: str
    is_default: bool = False

    @field_validator("state")
    @classmethod
    def _v_state_create(cls, v): return _v_state(v)


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_default: Optional[bool] = None

    @field_validator("state")
    @classmethod
    def _v_state_update(cls, v): return _v_state(v)


class AddressOut(BaseModel):
    id: int
    label: str
    name: str
    phone: str
    address: str
    city: str
    state: Optional[str] = None
    pincode: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True
