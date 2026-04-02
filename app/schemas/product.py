from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ProductImageOut(BaseModel):
    id: int
    image_url: str
    is_primary: bool
    sort_order: int

    class Config:
        from_attributes = True


class ProductVariantCreate(BaseModel):
    variant_type: str
    variant_value: str
    price_adjustment: float = 0.0
    stock: int = 0
    sku: Optional[str] = None


class ProductVariantUpdate(BaseModel):
    variant_type: Optional[str] = None
    variant_value: Optional[str] = None
    price_adjustment: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None


class ProductVariantOut(BaseModel):
    id: int
    variant_type: str
    variant_value: str
    price_adjustment: float
    stock: int
    sku: Optional[str]

    class Config:
        from_attributes = True


class DiscountSlabCreate(BaseModel):
    min_quantity: int
    discount_percentage: float


class DiscountSlabUpdate(BaseModel):
    min_quantity: Optional[int] = None
    discount_percentage: Optional[float] = None


class DiscountSlabOut(BaseModel):
    id: int
    min_quantity: int
    discount_percentage: float

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subcategory_id: int
    base_price: float
    is_active: bool = True
    has_variants: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subcategory_id: Optional[int] = None
    base_price: Optional[float] = None
    is_active: Optional[bool] = None
    has_variants: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    subcategory_id: int
    base_price: float
    is_active: bool
    has_variants: bool
    created_at: datetime
    images: List[ProductImageOut] = []
    variants: List[ProductVariantOut] = []
    discount_slabs: List[DiscountSlabOut] = []

    class Config:
        from_attributes = True
