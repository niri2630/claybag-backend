from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ProductImageOut(BaseModel):
    id: int
    image_url: str
    is_primary: bool
    sort_order: int
    variant_id: Optional[int] = None

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
    variant_id: Optional[int] = None  # null = applies to all variants
    min_quantity: int
    # Either price_per_unit (new, preferred) OR discount_percentage (legacy)
    price_per_unit: Optional[float] = None
    discount_percentage: Optional[float] = None


class DiscountSlabUpdate(BaseModel):
    variant_id: Optional[int] = None
    min_quantity: Optional[int] = None
    price_per_unit: Optional[float] = None
    discount_percentage: Optional[float] = None


class DiscountSlabOut(BaseModel):
    id: int
    variant_id: Optional[int] = None
    min_quantity: int
    price_per_unit: Optional[float] = None
    discount_percentage: Optional[float] = None

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    specifications: Optional[str] = None
    use_cases: Optional[str] = None
    materials: Optional[str] = None
    delivery_info: Optional[str] = None
    branding_info: Optional[str] = None
    subcategory_id: int
    base_price: float
    is_active: bool = True
    has_variants: bool = False
    is_featured: bool = False
    min_order_qty: Optional[int] = None  # null = no MOQ
    size_chart_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    use_cases: Optional[str] = None
    materials: Optional[str] = None
    delivery_info: Optional[str] = None
    branding_info: Optional[str] = None
    subcategory_id: Optional[int] = None
    base_price: Optional[float] = None
    is_active: Optional[bool] = None
    has_variants: Optional[bool] = None
    is_featured: Optional[bool] = None
    min_order_qty: Optional[int] = None
    size_chart_url: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    use_cases: Optional[str] = None
    materials: Optional[str] = None
    delivery_info: Optional[str] = None
    branding_info: Optional[str] = None
    subcategory_id: int
    base_price: float
    is_active: bool = True
    has_variants: bool = False
    is_featured: bool = False
    min_order_qty: Optional[int] = None
    size_chart_url: Optional[str] = None
    variant_mode: str = "multi_qty"  # from parent category
    created_at: datetime
    images: List[ProductImageOut] = []
    variants: List[ProductVariantOut] = []
    discount_slabs: List[DiscountSlabOut] = []

    class Config:
        from_attributes = True
