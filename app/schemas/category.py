from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CategoryCreate(BaseModel):
    name: str
    slug: str
    icon: str = "category"
    image_url: Optional[str] = None
    is_active: bool = True
    variant_mode: str = "multi_qty"  # "multi_qty" | "single_select"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    variant_mode: Optional[str] = None


class SubCategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    category_id: int
    image_url: Optional[str]
    is_active: bool
    product_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    icon: str = "category"
    image_url: Optional[str]
    is_active: bool
    variant_mode: str = "multi_qty"
    created_at: datetime
    subcategories: List[SubCategoryOut] = []

    class Config:
        from_attributes = True


class SubCategoryCreate(BaseModel):
    name: str
    slug: str
    category_id: int
    image_url: Optional[str] = None
    is_active: bool = True


class SubCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
