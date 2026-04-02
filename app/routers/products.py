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


@router.get("", response_model=List[ProductOut])
def list_products(
    subcategory_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    q = db.query(Product).filter(Product.is_active == True)
    if subcategory_id:
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
    return q.offset(skip).limit(limit).all()


@router.get("/all", response_model=List[ProductOut])
def list_all_products(
    subcategory_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    q = db.query(Product)
    if subcategory_id:
        q = q.filter(Product.subcategory_id == subcategory_id)
    return q.offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return p


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    p = Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


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
    for k, v in data.model_dump(exclude_none=True).items():
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
