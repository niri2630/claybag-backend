from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CategoryCreate(BaseModel):
    name: str
    slug: str
    image_url: Optional[str] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class SubCategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    category_id: int
    image_url: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    image_url: Optional[str]
    is_active: bool
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
