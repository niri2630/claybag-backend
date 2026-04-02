import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product, ProductImage
from app.schemas.product import ProductImageOut
from app.core.security import get_current_admin
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def save_file(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WEBP allowed")
    ext = file.filename.rsplit(".", 1)[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return f"/uploads/{filename}"


@router.post("/products/{product_id}/images", response_model=ProductImageOut)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise HTTPException(404, "Product not found")
    if is_primary:
        db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_primary": False})
    image_url = save_file(file)
    count = db.query(ProductImage).filter(ProductImage.product_id == product_id).count()
    img = ProductImage(
        product_id=product_id,
        image_url=image_url,
        is_primary=is_primary or count == 0,
        sort_order=count
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


@router.delete("/products/{product_id}/images/{image_id}")
def delete_product_image(product_id: int, image_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    img = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not img:
        raise HTTPException(404, "Image not found")
    # Remove file from disk safely (avoid path traversal)
    local_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(img.image_url))
    if os.path.exists(local_path):
        os.remove(local_path)
    db.delete(img)
    db.commit()
    return {"detail": "Deleted"}


@router.post("/categories/{category_id}/image")
def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    from app.models.category import Category
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    image_url = save_file(file)
    cat.image_url = image_url
    db.commit()
    return {"image_url": image_url}
