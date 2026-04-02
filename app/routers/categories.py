from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.category import Category, SubCategory
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryOut,
    SubCategoryCreate, SubCategoryUpdate, SubCategoryOut
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/categories", tags=["categories"])


# ── Categories ──────────────────────────────────────────────────────────────

@router.get("", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).all()


@router.get("/all", response_model=List[CategoryOut])
def list_all_categories(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return db.query(Category).all()


@router.get("/slug/{slug}", response_model=CategoryOut)
def get_category_by_slug(slug: str, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.slug == slug, Category.is_active == True).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.post("", response_model=CategoryOut)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    if db.query(Category).filter(Category.slug == data.slug).first():
        raise HTTPException(400, "Slug already exists")
    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    db.delete(cat)
    db.commit()
    return {"detail": "Deleted"}


# ── Sub-Categories ───────────────────────────────────────────────────────────

@router.get("/{category_id}/subcategories", response_model=List[SubCategoryOut])
def list_subcategories(category_id: int, db: Session = Depends(get_db)):
    return db.query(SubCategory).filter(
        SubCategory.category_id == category_id,
        SubCategory.is_active == True
    ).all()


@router.post("/subcategories", response_model=SubCategoryOut)
def create_subcategory(data: SubCategoryCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    if db.query(SubCategory).filter(SubCategory.slug == data.slug).first():
        raise HTTPException(400, "Slug already exists")
    sub = SubCategory(**data.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.put("/subcategories/{sub_id}", response_model=SubCategoryOut)
def update_subcategory(sub_id: int, data: SubCategoryUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    sub = db.query(SubCategory).filter(SubCategory.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "SubCategory not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/subcategories/{sub_id}")
def delete_subcategory(sub_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    sub = db.query(SubCategory).filter(SubCategory.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "SubCategory not found")
    db.delete(sub)
    db.commit()
    return {"detail": "Deleted"}
