import re
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.product import Product, ProductVariant, DiscountSlab
from app.models.category import Category, SubCategory
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductVariantCreate, ProductVariantUpdate, ProductVariantOut,
    DiscountSlabCreate, DiscountSlabUpdate, DiscountSlabOut
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/products", tags=["products"])

# All available branding methods
ALL_BRANDING_METHODS = [
    "Embroidery", "Screen Printing", "Sublimation Print",
    "Digital Printing", "Embossing", "UV Printing",
    "UV DTF Printing", "Laser Engraving", "Vinyl Heat Press",
]

# Default branding methods by category name (case-insensitive match)
DEFAULT_BRANDING_BY_CATEGORY = {
    "apparel": ["Embroidery", "Screen Printing", "Sublimation Print", "Vinyl Heat Press"],
    "t-shirts": ["Embroidery", "Screen Printing", "Sublimation Print", "Vinyl Heat Press"],
    "clothing": ["Embroidery", "Screen Printing", "Sublimation Print", "Vinyl Heat Press"],
    "drinkware": ["UV Printing", "Sublimation Print", "Laser Engraving"],
    "bottles": ["UV Printing", "Sublimation Print", "Laser Engraving"],
    "mugs": ["UV Printing", "Sublimation Print", "Laser Engraving"],
    "bags": ["Screen Printing", "Embroidery", "Digital Printing"],
    "stationery": ["UV Printing", "Screen Printing", "Digital Printing"],
    "tech": ["UV Printing", "Laser Engraving", "UV DTF Printing"],
    "electronics": ["UV Printing", "Laser Engraving", "UV DTF Printing"],
    "awards": ["Laser Engraving", "UV Printing", "Embossing"],
    "lanyards": ["Screen Printing", "Sublimation Print", "Digital Printing"],
}


def _slugify(text: str) -> str:
    """Convert a product name to a URL-safe slug."""
    if not text:
        return ""
    # Lowercase, replace non-alphanumeric with hyphens
    s = re.sub(r"[^a-z0-9]+", "-", text.lower())
    # Strip leading/trailing hyphens
    s = s.strip("-")
    # Collapse multiple hyphens
    s = re.sub(r"-+", "-", s)
    return s[:200]  # cap length


def _generate_unique_slug(db: Session, name: str, exclude_id: Optional[int] = None) -> str:
    """Generate a unique slug. Append -2, -3 etc if conflicts exist."""
    base = _slugify(name) or "product"
    slug = base
    n = 2
    while True:
        q = db.query(Product).filter(Product.slug == slug)
        if exclude_id is not None:
            q = q.filter(Product.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


def _get_variant_mode(p: Product, db: Session) -> str:
    """Determine variant_mode for a product.
    Priority:
      1. p.variant_mode_override if set (admin-chosen, e.g. "option_dropdown").
      2. "single_select" if product has 2+ distinct variant types (e.g. size + color).
      3. Parent category's variant_mode.
      4. Default "multi_qty".
    """
    if getattr(p, "variant_mode_override", None):
        return p.variant_mode_override
    if p.variants:
        distinct_types = set(v.variant_type.lower() for v in p.variants)
        if len(distinct_types) > 1:
            return "single_select"
    sub = db.query(SubCategory).filter(SubCategory.id == p.subcategory_id).first()
    if sub:
        cat = db.query(Category).filter(Category.id == sub.category_id).first()
        if cat:
            return cat.variant_mode
    return "multi_qty"


def _enrich_product(p: Product, db: Session) -> dict:
    """Add variant_mode and deserialize branding_methods."""
    data = ProductOut.model_validate(p).model_dump()
    data["variant_mode"] = _get_variant_mode(p, db)
    # Deserialize branding_methods from JSON string
    if p.branding_methods:
        try:
            data["branding_methods"] = json.loads(p.branding_methods)
        except (json.JSONDecodeError, TypeError):
            data["branding_methods"] = None
    return data


def _enrich_products(products: list, db: Session) -> list:
    """Bulk enrich with variant_mode."""
    cat_cache = {}  # subcategory_id -> variant_mode
    result = []
    for p in products:
        data = ProductOut.model_validate(p).model_dump()
        # 1. Per-product override wins (admin-chosen, e.g. "option_dropdown")
        if getattr(p, "variant_mode_override", None):
            data["variant_mode"] = p.variant_mode_override
            result.append(data)
            continue
        # 2. Multi-type → single_select auto
        if p.variants:
            distinct_types = set(v.variant_type.lower() for v in p.variants)
            if len(distinct_types) > 1:
                data["variant_mode"] = "single_select"
                result.append(data)
                continue
        # 3. Fall back to category setting
        if p.subcategory_id not in cat_cache:
            sub = db.query(SubCategory).filter(SubCategory.id == p.subcategory_id).first()
            if sub:
                cat = db.query(Category).filter(Category.id == sub.category_id).first()
                cat_cache[p.subcategory_id] = cat.variant_mode if cat else "multi_qty"
            else:
                cat_cache[p.subcategory_id] = "multi_qty"
        data["variant_mode"] = cat_cache[p.subcategory_id]
        result.append(data)
    return result


@router.get("", response_model=List[ProductOut])
def list_products(
    subcategory_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Product).filter(Product.is_active == True)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    elif subcategory_id:
        q = q.filter(Product.subcategory_id == subcategory_id)
    elif category_slug:
        cat = db.query(Category).filter(Category.slug == category_slug).first()
        if cat:
            sub_ids = [s.id for s in db.query(SubCategory).filter(SubCategory.category_id == cat.id).all()]
            if sub_ids:
                q = q.filter(Product.subcategory_id.in_(sub_ids))
            else:
                return []
        else:
            return []
    q = q.order_by(Product.id.desc())
    if skip:
        q = q.offset(skip)
    if limit:
        q = q.limit(limit)
    return _enrich_products(q.all(), db)


@router.get("/featured", response_model=List[ProductOut])
def list_featured_products(db: Session = Depends(get_db)):
    """Get products marked as featured (hot sellers)."""
    products = db.query(Product).filter(Product.is_active == True, Product.is_featured == True).all()
    return _enrich_products(products, db)


@router.get("/new-arrivals", response_model=List[ProductOut])
def list_new_arrivals(limit: int = 30, db: Session = Depends(get_db)):
    """Public new arrivals feed.

    Behavior:
      1. If any active products are flagged is_new_arrival=True, return only those
         (newest first). This is the admin-curated path.
      2. Otherwise fall back to the newest active products by created_at desc
         (so the page is never empty on a fresh install).
    Default limit is 30. Capped between 1 and 100.
    """
    if limit < 1: limit = 1
    if limit > 100: limit = 100
    flagged = (
        db.query(Product)
        .filter(Product.is_active == True, Product.is_new_arrival == True)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .limit(limit)
        .all()
    )
    if flagged:
        return _enrich_products(flagged, db)
    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .limit(limit)
        .all()
    )
    return _enrich_products(products, db)


@router.get("/all", response_model=List[ProductOut])
def list_all_products(
    subcategory_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    q = db.query(Product)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    elif subcategory_id:
        q = q.filter(Product.subcategory_id == subcategory_id)
    q = q.order_by(Product.id.desc())
    if skip:
        q = q.offset(skip)
    if limit:
        q = q.limit(limit)
    return _enrich_products(q.all(), db)


@router.get("/slug/{slug}", response_model=ProductOut)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.slug == slug).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return _enrich_product(p, db)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return _enrich_product(p, db)


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    payload = data.model_dump()
    # Serialize branding_methods list to JSON string
    if payload.get("branding_methods") is not None:
        payload["branding_methods"] = json.dumps(payload["branding_methods"])
    else:
        # Auto-populate branding methods based on category
        sub = db.query(SubCategory).filter(SubCategory.id == payload["subcategory_id"]).first()
        if sub:
            cat = db.query(Category).filter(Category.id == sub.category_id).first()
            if cat:
                cat_key = cat.name.lower().strip()
                defaults = DEFAULT_BRANDING_BY_CATEGORY.get(cat_key, DEFAULT_BRANDING_BY_CATEGORY.get("default", ALL_BRANDING_METHODS[:3]))
                # Also check subcategory name
                sub_key = sub.name.lower().strip()
                if sub_key in DEFAULT_BRANDING_BY_CATEGORY:
                    defaults = DEFAULT_BRANDING_BY_CATEGORY[sub_key]
                payload["branding_methods"] = json.dumps(defaults)
    p = Product(**payload)
    p.slug = _generate_unique_slug(db, payload["name"])
    db.add(p)
    db.commit()
    db.refresh(p)
    return _enrich_product(p, db)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    update = data.model_dump(exclude_none=True)
    # Serialize branding_methods list to JSON string
    if "branding_methods" in update and isinstance(update["branding_methods"], list):
        update["branding_methods"] = json.dumps(update["branding_methods"])
    name_changed = "name" in update and update["name"] != p.name
    for k, v in update.items():
        setattr(p, k, v)
    # Regenerate slug if name changed or slug is missing
    if name_changed or not p.slug:
        p.slug = _generate_unique_slug(db, p.name, exclude_id=p.id)
    db.commit()
    db.refresh(p)
    return _enrich_product(p, db)


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    # Check if product has associated orders — if so, soft-delete instead
    from app.models.order import OrderItem
    has_orders = db.query(OrderItem).filter(OrderItem.product_id == product_id).first()
    if has_orders:
        p.is_active = False
        db.commit()
        return {"detail": "Product has existing orders and was deactivated instead of deleted."}
    db.delete(p)
    db.commit()
    return {"detail": "Deleted"}


# ── Variants ─────────────────────────────────────────────────────────────────

@router.post("/{product_id}/variants", response_model=ProductVariantOut)
def add_variant(product_id: int, data: ProductVariantCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise HTTPException(404, "Product not found")
    v = ProductVariant(product_id=product_id, **data.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariantOut)
def update_variant(product_id: int, variant_id: int, data: ProductVariantUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    v = db.query(ProductVariant).filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id).first()
    if not v:
        raise HTTPException(404, "Variant not found")
    for k, val in data.model_dump(exclude_none=True).items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/{product_id}/variants/{variant_id}")
def delete_variant(product_id: int, variant_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    v = db.query(ProductVariant).filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id).first()
    if not v:
        raise HTTPException(404, "Variant not found")
    db.delete(v)
    db.commit()
    return {"detail": "Deleted"}


# ── Discount Slabs ────────────────────────────────────────────────────────────

@router.post("/{product_id}/discounts", response_model=DiscountSlabOut)
def add_discount_slab(product_id: int, data: DiscountSlabCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise HTTPException(404, "Product not found")
    slab = DiscountSlab(product_id=product_id, **data.model_dump())
    db.add(slab)
    db.commit()
    db.refresh(slab)
    return slab


@router.put("/{product_id}/discounts/{slab_id}", response_model=DiscountSlabOut)
def update_discount_slab(product_id: int, slab_id: int, data: DiscountSlabUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    slab = db.query(DiscountSlab).filter(DiscountSlab.id == slab_id, DiscountSlab.product_id == product_id).first()
    if not slab:
        raise HTTPException(404, "Discount slab not found")
    # Use exclude_unset so explicitly sent null values (like variant_id: null)
    # are applied, while omitted fields are left unchanged.
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(slab, k, v)
    db.commit()
    db.refresh(slab)
    return slab


@router.delete("/{product_id}/discounts/{slab_id}")
def delete_discount_slab(product_id: int, slab_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    slab = db.query(DiscountSlab).filter(DiscountSlab.id == slab_id, DiscountSlab.product_id == product_id).first()
    if not slab:
        raise HTTPException(404, "Discount slab not found")
    db.delete(slab)
    db.commit()
    return {"detail": "Deleted"}
