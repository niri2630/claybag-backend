import os
import io
import uuid
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from PIL import Image

from app.database import get_db
from app.models.product import Product, ProductImage
from app.schemas.product import ProductImageOut
from app.core.security import get_current_admin
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB — allows high-res product photography
PRODUCT_IMAGE_SIZE = (500, 500)  # Target size for product images


def _is_s3_enabled() -> bool:
    return bool(settings.S3_BUCKET and settings.S3_PUBLIC_URL)


def _get_s3_client():
    import boto3
    return boto3.client("s3", region_name=settings.S3_REGION)


def _resize_to_square(data: bytes, size: tuple = PRODUCT_IMAGE_SIZE) -> Tuple[bytes, str]:
    """Resize image to a square (e.g. 500x500) with high quality.
    Crops to center square first, then resizes. Returns (bytes, content_type)."""
    img = Image.open(io.BytesIO(data))

    # Convert RGBA/P to RGB for JPEG compatibility
    if img.mode in ("RGBA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = bg

    # Center-crop to square
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    # Resize to target using high-quality Lanczos filter
    img = img.resize(size, Image.LANCZOS)

    # Save as JPEG with high quality (95) to preserve detail
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue(), "image/jpeg"


def save_file(file: UploadFile, resize: bool = True) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WEBP allowed")

    # Read file and check size
    data = file.file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    content_type = file.content_type
    ext = "jpg"

    # Resize product images to 500x500 square
    if resize:
        try:
            data, content_type = _resize_to_square(data)
            ext = "jpg"
        except Exception:
            # If resize fails, upload original
            ext = (file.filename or "image").rsplit(".", 1)[-1].lower()
            if ext not in {"jpg", "jpeg", "png", "webp"}:
                ext = "jpg"
    else:
        ext = (file.filename or "image").rsplit(".", 1)[-1].lower()
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            ext = "jpg"

    filename = f"{uuid.uuid4()}.{ext}"

    if _is_s3_enabled():
        # Upload to S3 — persistent across container restarts
        s3 = _get_s3_client()
        key = f"products/{filename}"
        try:
            s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        except Exception as e:
            raise HTTPException(500, f"S3 upload failed: {str(e)}")
        # Return absolute S3 URL so the frontend can render it directly
        return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{key}"

    # Local fallback (development only)
    path = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return f"/media/{filename}"


def delete_stored_file(image_url: str) -> None:
    """Best-effort delete from S3 or local disk."""
    if not image_url:
        return
    if _is_s3_enabled() and image_url.startswith(settings.S3_PUBLIC_URL):
        # Strip the public URL prefix to get the S3 key
        key = image_url[len(settings.S3_PUBLIC_URL):].lstrip("/")
        try:
            _get_s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
        except Exception:
            pass
    else:
        # Local file
        local_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(image_url))
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass


@router.post("/products/{product_id}/images", response_model=ProductImageOut)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    variant_id: Optional[int] = None,
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
        variant_id=variant_id,
        image_url=image_url,
        is_primary=is_primary or count == 0,
        sort_order=count
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


@router.put("/products/{product_id}/images/{image_id}/variant", response_model=ProductImageOut)
def update_image_variant(
    product_id: int,
    image_id: int,
    variant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    """Tag or untag an existing image with a variant (e.g. color)."""
    img = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not img:
        raise HTTPException(404, "Image not found")
    img.variant_id = variant_id
    db.commit()
    db.refresh(img)
    return img


@router.post("/products/{product_id}/images/batch", response_model=List[ProductImageOut])
def upload_product_images_batch(
    product_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    """Upload multiple images at once. The first uploaded image becomes primary
    if the product has no existing images. Subsequent images become secondary."""
    if not db.query(Product).filter(Product.id == product_id).first():
        raise HTTPException(404, "Product not found")
    if not files:
        raise HTTPException(400, "No files provided")

    existing_count = db.query(ProductImage).filter(ProductImage.product_id == product_id).count()
    has_primary = db.query(ProductImage).filter(
        ProductImage.product_id == product_id,
        ProductImage.is_primary == True
    ).first() is not None

    saved: List[ProductImage] = []
    for idx, file in enumerate(files):
        try:
            image_url = save_file(file)
        except HTTPException:
            # Skip individual failures so the batch can continue
            continue
        # First file becomes primary only if no existing primary
        is_primary = (idx == 0) and not has_primary
        if is_primary:
            has_primary = True  # Subsequent ones in this batch stay secondary
        img = ProductImage(
            product_id=product_id,
            image_url=image_url,
            is_primary=is_primary,
            sort_order=existing_count + idx,
        )
        db.add(img)
        saved.append(img)

    db.commit()
    for img in saved:
        db.refresh(img)
    return saved


@router.delete("/products/{product_id}/images/{image_id}")
def delete_product_image(product_id: int, image_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    img = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not img:
        raise HTTPException(404, "Image not found")
    delete_stored_file(img.image_url)
    db.delete(img)
    db.commit()
    return {"detail": "Deleted"}


@router.post("/size-chart/{product_id}")
def upload_size_chart(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Upload a size chart image for a product. Saves to S3/disk and updates product.size_chart_url."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WEBP allowed")

    data = file.file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")

    ext = (file.filename or "image").rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    filename = f"size-chart-{product_id}-{uuid.uuid4().hex[:8]}.{ext}"

    if _is_s3_enabled():
        s3 = _get_s3_client()
        key = f"size-charts/{filename}"
        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        url = f"{settings.S3_PUBLIC_URL.rstrip('/')}/{key}"
    else:
        path = os.path.join(settings.UPLOAD_DIR, filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        url = f"/media/{filename}"

    # Delete old chart from storage if exists
    if product.size_chart_url:
        delete_stored_file(product.size_chart_url)

    product.size_chart_url = url
    db.commit()
    return {"url": url}


@router.put("/products/{product_id}/images/{image_id}/primary")
def set_primary_image(product_id: int, image_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Set an image as the primary image for a product. Un-primaries all others."""
    img = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not img:
        raise HTTPException(404, "Image not found")
    # Un-primary all images for this product
    db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_primary": False})
    # Set this one as primary
    img.is_primary = True
    db.commit()
    return {"detail": "Primary image updated"}


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
