import re
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
    """Determine variant_mode per product based on its actual variant types.
    If product has 2+ distinct variant types (e.g. size + color), use single_select.
    Otherwise fall back to the category's variant_mode or multi_qty."""
    if p.variants:
        distinct_types = set(v.variant_type.lower() for v in p.variants)
        if len(distinct_types) > 1:
            return "single_select"
    # Fall back to category setting
    sub = db.query(SubCategory).filter(SubCategory.id == p.subcategory_id).first()
    if sub:
        cat = db.query(Category).filter(Category.id == sub.category_id).first()
        if cat:
            return cat.variant_mode
    return "multi_qty"


def _enrich_product(p: Product, db: Session) -> dict:
    """Add variant_mode to the response based on product's variant types."""
    data = ProductOut.model_validate(p).model_dump()
    data["variant_mode"] = _get_variant_mode(p, db)
    return data


def _enrich_products(products: list, db: Session) -> list:
    """Bulk enrich with variant_mode."""
    cat_cache = {}  # subcategory_id -> variant_mode
    result = []
    for p in products:
        data = ProductOut.model_validate(p).model_dump()
        # Check if product has multiple variant types
        if p.variants:
            distinct_types = set(v.variant_type.lower() for v in p.variants)
            if len(distinct_types) > 1:
                data["variant_mode"] = "single_select"
                result.append(data)
                continue
        # Fall back to category setting
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
