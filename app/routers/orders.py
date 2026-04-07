from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple

from app.database import get_db
from app.models.order import Order, OrderItem, OrderTracking, OrderStatus
from app.models.product import Product, ProductVariant, ProductImage, DiscountSlab
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/orders", tags=["orders"])


def _enrich_order(order: Order, db: Session) -> dict:
    """Populate product_name, product_slug, product_image and variant_label on each item."""
    data = OrderOut.model_validate(order).model_dump()
    if not data.get("items"):
        return data

    product_ids = {it["product_id"] for it in data["items"]}
    variant_ids = {it["variant_id"] for it in data["items"] if it.get("variant_id")}

    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()} if product_ids else {}
    variants = {v.id: v for v in db.query(ProductVariant).filter(ProductVariant.id.in_(variant_ids)).all()} if variant_ids else {}

    # Primary image per product
    images: dict[int, str] = {}
    if product_ids:
        rows = db.query(ProductImage).filter(ProductImage.product_id.in_(product_ids)).order_by(ProductImage.is_primary.desc(), ProductImage.sort_order.asc()).all()
        for img in rows:
            if img.product_id not in images:
                images[img.product_id] = img.image_url

    for it in data["items"]:
        prod = products.get(it["product_id"])
        if prod:
            it["product_name"] = prod.name
            it["product_slug"] = prod.slug
            it["product_image"] = images.get(prod.id)
        if it.get("variant_id"):
            v = variants.get(it["variant_id"])
            if v:
                it["variant_label"] = f"{v.variant_type.capitalize()}: {v.variant_value}"
    return data


def _enrich_orders(orders: list, db: Session) -> list:
    return [_enrich_order(o, db) for o in orders]


def calculate_price(product: Product, variant: Optional[ProductVariant], quantity: int, db: Session) -> Tuple[float, float]:
    base = product.base_price + (variant.price_adjustment if variant else 0)
    slabs = db.query(DiscountSlab).filter(
        DiscountSlab.product_id == product.id,
        DiscountSlab.min_quantity <= quantity
    ).order_by(DiscountSlab.min_quantity.desc()).first()
    discount = slabs.discount_percentage if slabs else 0.0
    final = base * (1 - discount / 100) * quantity
    return final, discount


@router.post("", response_model=OrderOut)
def create_order(data: OrderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    total = 0.0
    items_to_create = []
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(404, f"Product {item.product_id} not found")
        variant = None
        if item.variant_id:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        item_total, discount = calculate_price(product, variant, item.quantity, db)
        unit_price = product.base_price + (variant.price_adjustment if variant else 0)
        total += item_total
        items_to_create.append((item, unit_price, item_total, discount))

    order = Order(
        user_id=current_user.id,
        total_amount=total,
        shipping_name=data.shipping_name,
        shipping_phone=data.shipping_phone,
        shipping_address=data.shipping_address,
        shipping_city=data.shipping_city,
        shipping_pincode=data.shipping_pincode,
        notes=data.notes,
    )
    db.add(order)
    db.flush()

    for item, unit_price, item_total, discount in items_to_create:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=item_total,
            discount_applied=discount,
        ))

    db.add(OrderTracking(order_id=order.id, status=OrderStatus.PENDING, note="Order placed"))
    db.commit()
    db.refresh(order)
    return _enrich_order(order, db)


@router.get("", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.is_admin:
        orders = db.query(Order).order_by(Order.created_at.desc()).all()
    else:
        orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()
    return _enrich_orders(orders, db)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _enrich_order(order, db)


@router.put("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = data.status
    db.add(OrderTracking(order_id=order.id, status=data.status, note=data.note))
    db.commit()
    db.refresh(order)
    return _enrich_order(order, db)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Customer cancels their own order (e.g. cancelled payment in Cashfree modal)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    if order.payment_status == "PAID":
        raise HTTPException(400, "Cannot cancel a paid order. Contact support for refund.")
    if order.status == OrderStatus.CANCELLED:
        return _enrich_order(order, db)
    order.status = OrderStatus.CANCELLED
    order.payment_status = "CANCELLED"
    db.add(OrderTracking(order_id=order.id, status=OrderStatus.CANCELLED, note="Customer cancelled payment"))
    db.commit()
    db.refresh(order)
    return _enrich_order(order, db)
