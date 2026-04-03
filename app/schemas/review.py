from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ReviewCreate(BaseModel):
    product_id: int
    rating: int  # 1-5
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: Optional[str]
    is_approved: bool
    created_at: datetime
    user_name: str = ""
    product_name: str = ""

    class Config:
        from_attributes = True
