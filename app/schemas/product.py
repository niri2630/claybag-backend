from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
import json

# Valid GST rates as per Indian tax regulations
_VALID_GST_RATES = {0, 5, 12, 18, 28}


def _validate_gst_rate(v):
    if v is None:
        return v
    # Accept floats and ints; round to nearest 0.01
    rate = round(float(v), 2)
    if rate < 0 or rate > 100:
        raise ValueError("gst_rate must be between 0 and 100")
    # Common rates only — flag unusual values but allow them (some products may have custom)
    return rate


def _validate_hsn_code(v):
    if v is None or v == "":
        return None
    s = str(v).strip().upper().replace(" ", "")
    if len(s) > 10:
        raise ValueError("hsn_code max length is 10")
    # HSN should be alphanumeric only
    if not s.isalnum():
        raise ValueError("hsn_code must be alphanumeric only")
    return s


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
    branding_methods: Optional[List[str]] = None
    subcategory_id: int
    base_price: float
    compare_price: Optional[float] = None  # Original/MRP price (strikethrough)
    is_active: bool = True
    has_variants: bool = False
    is_featured: bool = False
    min_order_qty: Optional[int] = None  # null = no MOQ
    moq_unit: Optional[str] = None  # "pcs", "sq.in", "kg", etc. Default "pcs".
    pricing_mode: Optional[str] = None  # "per_unit" (default) or "per_area"
    size_chart_url: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None

    @field_validator("gst_rate")
    @classmethod
    def _v_gst(cls, v): return _validate_gst_rate(v)

    @field_validator("hsn_code")
    @classmethod
    def _v_hsn(cls, v): return _validate_hsn_code(v)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    use_cases: Optional[str] = None
    materials: Optional[str] = None
    delivery_info: Optional[str] = None
    branding_info: Optional[str] = None
    branding_methods: Optional[List[str]] = None
    subcategory_id: Optional[int] = None
    base_price: Optional[float] = None
    compare_price: Optional[float] = None
    is_active: Optional[bool] = None
    has_variants: Optional[bool] = None
    is_featured: Optional[bool] = None
    min_order_qty: Optional[int] = None
    moq_unit: Optional[str] = None
    pricing_mode: Optional[str] = None
    size_chart_url: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None

    @field_validator("gst_rate")
    @classmethod
    def _v_gst(cls, v): return _validate_gst_rate(v)

    @field_validator("hsn_code")
    @classmethod
    def _v_hsn(cls, v): return _validate_hsn_code(v)


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
    branding_methods: Optional[List[str]] = None
    subcategory_id: int
    base_price: float
    compare_price: Optional[float] = None
    is_active: bool = True
    has_variants: bool = False
    is_featured: bool = False
    min_order_qty: Optional[int] = None
    moq_unit: Optional[str] = "pcs"
    pricing_mode: Optional[str] = "per_unit"
    size_chart_url: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    variant_mode: str = "multi_qty"  # from parent category
    created_at: datetime
    images: List[ProductImageOut] = []
    variants: List[ProductVariantOut] = []
    discount_slabs: List[DiscountSlabOut] = []

    @field_validator("branding_methods", mode="before")
    @classmethod
    def parse_branding_methods(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True
