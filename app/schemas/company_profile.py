from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CompanyProfileCreate(BaseModel):
    company_name: str
    business_type: str  # private_limited, partnership, sole_proprietor, llp, other
    gst_number: Optional[str] = None
    registered_address: Optional[str] = None
    contact_person: Optional[str] = None
    description: Optional[str] = None


class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    gst_number: Optional[str] = None
    registered_address: Optional[str] = None
    contact_person: Optional[str] = None
    description: Optional[str] = None


class CompanyProfileOut(BaseModel):
    id: int
    user_id: int
    company_name: str
    business_type: str
    gst_number: Optional[str]
    registered_address: Optional[str]
    contact_person: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
