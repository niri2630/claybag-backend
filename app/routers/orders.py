import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple

from app.database import get_db
from app.models.order import Order, OrderItem, OrderTracking, OrderStatus
from app.models.product import Product, ProductVariant, ProductImage, DiscountSlab
from app.models.user import User
from app.models.wallet import Wallet, WalletTransaction
from app.models.referral import Referral
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.core.security import get_current_user, get_current_admin
from app.core.config import settings


def _normalize_state(s: Optional[str]) -> str:
    """Lowercase + strip for state comparison (handles 'Karnataka', 'karnataka ', etc.)."""
    return (s or "").strip().lower()


def _split_gst(taxable: float, rate: float, intra_state: bool) -> Dict[str, float]:
    """Compute CGST/SGST or IGST given taxable amount and GST rate.
    intra_state=True (buyer in our state) → split as CGST+SGST.
    intra_state=False → full IGST.
    """
    tax = round(taxable * (rate / 100.0), 2)
    if intra_state:
        half = round(tax / 2.0, 2)
        return {"cgst": half, "sgst": tax - half, "igst": 0.0}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax}

router = APIRouter(prefix="/orders", tags=["orders"])


# Order number generation — random jumping numeric, non-sequential.
# Looks natural: 4729, 18234, 7891, 52103, etc.
# Range: 1000–99999 (5 digits max, ~90K possibilities).
# Once we have 50K+ orders, range auto-expands to 6 digits.

def _generate_order_number(db: Session, max_attempts: int = 20) -> str:
    """Generate a unique random order number like 'CB-4729' or 'CB-18234'.
    Random jumping numbers — non-sequential, looks organic."""
    for _ in range(max_attempts):
        num = secrets.randbelow(9900) + 100  # 100–9999
        candidate = f"CB-{num}"
        if not db.query(Order).filter(Order.order_number == candidate).first():
            return candidate
    # Fallback: expand to 5 digits if 100-9999 is exhausted
    return f"CB-{secrets.randbelow(90000) + 10000}"


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
    images: Dict[int, str] = {}
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


def _parse_variant_area(variant: ProductVariant) -> Optional[float]:
    """If a variant represents a sq.in size (variant_unit='sq.in' AND variant_value parses as a
    positive number), return that area. Otherwise return None.

    Used for per_area products where variants are preset sticker sizes (e.g. "40 sq.in").
    """
    if variant is None:
        return None
    unit = (variant.variant_unit or "").strip().lower()
    if unit not in ("sq.in", "sqin", "sq in", "sq.inches", "sq inches"):
        return None
    try:
        v = float(str(variant.variant_value).strip())
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def calculate_area_price(product: Product, length: Optional[float], breadth: Optional[float], quantity: int, db: Session, variant: Optional[ProductVariant] = None) -> Tuple[float, float, float, float]:
    """Per-area pricing for stickers/labels.

    Total area depends on path:
      - Variant path (sq.in size variant picked): area = variant_area × quantity
      - Custom L × B path (no variant or non-size variant): area = L × B × quantity

    Slab match against TOTAL AREA. Rate priority:
      1. Variant-scoped slab (variant_id == variant.id) → use slab.price_per_unit
      2. Product-wide slab (variant_id IS NULL) → use slab.price_per_unit
      3. Fallback rate:
           - Variant path: variant.price_adjustment / variant_area (implied base rate)
             so qty=1 gives exactly variant.price_adjustment as bundle price.
           - Custom L × B: product.base_price (₹/sq.in)
    Final = area × rate.
    """
    if quantity <= 0:
        raise HTTPException(400, f"Quantity must be greater than zero for {product.name}")

    variant_area = _parse_variant_area(variant) if variant is not None else None

    # Compute area
    if variant_area is not None:
        # Variant path: dimensions ignored; area derived from variant size × qty
        area = variant_area * quantity
    else:
        if length is None or breadth is None or length <= 0 or breadth <= 0:
            raise HTTPException(400, f"Product '{product.name}' requires positive length and breadth dimensions (inches)")
        area = length * breadth * quantity

    # Slab lookup — variant-scoped first, then product-wide
    slab = None
    if variant is not None:
        slab = db.query(DiscountSlab).filter(
            DiscountSlab.product_id == product.id,
            DiscountSlab.variant_id == variant.id,
            DiscountSlab.min_quantity <= area,
        ).order_by(DiscountSlab.min_quantity.desc()).first()
    if slab is None:
        slab = db.query(DiscountSlab).filter(
            DiscountSlab.product_id == product.id,
            DiscountSlab.variant_id.is_(None),
            DiscountSlab.min_quantity <= area,
        ).order_by(DiscountSlab.min_quantity.desc()).first()

    if slab and slab.price_per_unit is not None:
        rate = slab.price_per_unit
    elif slab and slab.discount_percentage:
        # Apply % off the implied base rate (variant) or product base_price
        if variant_area is not None and variant.price_adjustment:
            base_for_pct = variant.price_adjustment / variant_area
        else:
            base_for_pct = product.base_price
        rate = base_for_pct * (1 - slab.discount_percentage / 100.0)
    else:
        # No slab — use variant's implied rate (for size variants) or product base rate
        if variant_area is not None and variant.price_adjustment:
            rate = variant.price_adjustment / variant_area
        else:
            rate = product.base_price + (variant.price_adjustment if (variant is not None and variant_area is None) else 0.0)

    line_total = round(area * rate, 2)
    return line_total, area, rate, area


def calculate_price(product: Product, variant: Optional[ProductVariant], quantity: int, db: Session, aggregate_quantity: Optional[int] = None) -> Tuple[float, float]:
    """Compute line total + applied discount %.

    `aggregate_quantity` (optional) is the total quantity across ALL cart lines for this product
    (across colors/sizes for hybrid mode). Product-wide ("All Variants") slabs are matched against
    this aggregate so the slab applies whenever the order TOTAL meets the threshold, not just per-line.
    Variant-specific slabs still match against per-line quantity since they target a specific variant.
    Defaults to `quantity` when not provided.

    Pricing priority for a matched slab:
      1. price_per_unit: flat per-piece price (variant adjustment added on top).
      2. discount_percentage: % off base price.
      3. No slab: base price.
    """
    agg_qty = aggregate_quantity if aggregate_quantity is not None else quantity
    variant_adj = variant.price_adjustment if variant else 0
    base = product.base_price + variant_adj
    variant_id = variant.id if variant else None

    # Priority: variant-specific slab > product-wide slab
    # 1. Variant-specific slab — uses per-LINE quantity (slab targets this variant only)
    slab = None
    if variant_id:
        slab = db.query(DiscountSlab).filter(
            DiscountSlab.product_id == product.id,
            DiscountSlab.variant_id == variant_id,
            DiscountSlab.min_quantity <= quantity,
        ).order_by(DiscountSlab.min_quantity.desc()).first()

    # 2. Product-wide ("All Variants") slab — uses AGGREGATE quantity across all sibling lines
    if not slab:
        has_any_variant_slabs = db.query(DiscountSlab).filter(
            DiscountSlab.product_id == product.id,
            DiscountSlab.variant_id.isnot(None),
        ).first() is not None

        if not has_any_variant_slabs:
            slab = db.query(DiscountSlab).filter(
                DiscountSlab.product_id == product.id,
                DiscountSlab.variant_id.is_(None),
                DiscountSlab.min_quantity <= agg_qty,
            ).order_by(DiscountSlab.min_quantity.desc()).first()

    if slab:
        if slab.price_per_unit is not None:
            unit_price = slab.price_per_unit + variant_adj
            final = unit_price * quantity
            return final, 0.0
        discount = slab.discount_percentage or 0.0
        final = base * (1 - discount / 100) * quantity
        return final, discount

    return base * quantity, 0.0


@router.post("", response_model=OrderOut)
def create_order(data: OrderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Aggregate quantity per product across all line items (so "All Variants" slabs match
    # the order TOTAL across colors/sizes for hybrid products, not per-line).
    product_total_qty: dict = {}
    for it in data.items:
        product_total_qty[it.product_id] = product_total_qty.get(it.product_id, 0) + (it.quantity or 0)

    total = 0.0
    items_to_create = []
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(404, f"Product {item.product_id} not found")
        variant = None
        if item.variant_id:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()

        # Per-area (formula) pricing for stickers etc.
        # Two paths:
        #   A) Variant picked AND variant has sq.in size (e.g. variant_value="40", variant_unit="sq.in"):
        #      → area = variant_size × quantity (no L × B needed). Slab match on total area.
        #      → rate = slab.price_per_unit OR variant.price_adjustment / variant_size
        #   B) No variant (custom dimensions): area = L × B × quantity. Slab match on total area.
        #      → rate = slab.price_per_unit OR product.base_price
        if product.pricing_mode == "per_area":
            item_total, computed_area, area_rate, _ = calculate_area_price(
                product, item.dimension_length, item.dimension_breadth, item.quantity, db, variant=variant
            )
            # MOQ is in sq.in for per_area — validate against computed_area
            if product.min_order_qty and computed_area < product.min_order_qty:
                unit = product.moq_unit or "sq.in"
                raise HTTPException(400, f"Minimum order for '{product.name}' is {product.min_order_qty} {unit} (you requested {computed_area:.1f} {unit})")
            unit_price = area_rate  # per sq.in rate
            discount = 0.0
            area_info = {
                "length": item.dimension_length,
                "breadth": item.dimension_breadth,
                "area": computed_area,
                "rate": area_rate,
            }
        else:
            # per_unit standard variant + slab pricing
            agg_qty = product_total_qty.get(item.product_id, item.quantity)
            item_total, discount = calculate_price(product, variant, item.quantity, db, aggregate_quantity=agg_qty)
            unit_price = product.base_price + (variant.price_adjustment if variant else 0)
            area_info = None

        total += item_total
        # Snapshot HSN + GST rate for invoice
        gst_rate = product.gst_rate if product.gst_rate is not None else settings.DEFAULT_GST_RATE
        hsn_code = product.hsn_code
        items_to_create.append((item, unit_price, item_total, discount, hsn_code, gst_rate, area_info))

    # Apply 10% referral discount only if user opted in
    referral_discount = 0.0
    if data.use_referral_discount and current_user.referred_by:
        referral = db.query(Referral).filter(
            Referral.referred_id == current_user.id,
            Referral.discount_used == False,
        ).first()
        if referral:
            existing_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
            if existing_orders == 0:
                referral_discount = round(total * 0.10, 2)
                total = total - referral_discount
                referral.discount_used = True

    # Validate Clay Coins (deduction happens after payment confirmation)
    coins_applied = 0.0
    if data.coins_applied and data.coins_applied > 0:
        wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
        if not wallet or wallet.balance < data.coins_applied:
            raise HTTPException(400, "Insufficient Clay Coins balance")
        max_coins = total - 1.0
        if max_coins < 0:
            max_coins = 0
        coins_applied = min(data.coins_applied, max_coins)

    final_total = max(round(total - coins_applied, 2), 1.0)

    # GST breakdown (prices are inclusive of GST → back-calculate)
    intra_state = _normalize_state(data.shipping_state) == _normalize_state(settings.COMPANY_STATE)
    cgst_total = sgst_total = igst_total = 0.0
    taxable_total = 0.0
    # Distribute coins/referral discount proportionally per line so GST math stays accurate.
    # If discounts apply, scale each line proportionally.
    discount_scale = (final_total / total) if total > 0 else 1.0

    for _item, _u, item_total, _d, _hsn, gst_rate, _ai in items_to_create:
        line_after_discount = round(item_total * discount_scale, 2)
        # Inclusive: taxable = line / (1 + r/100); tax = line - taxable
        taxable = round(line_after_discount / (1.0 + gst_rate / 100.0), 2)
        split = _split_gst(taxable, gst_rate, intra_state)
        taxable_total += taxable
        cgst_total += split["cgst"]
        sgst_total += split["sgst"]
        igst_total += split["igst"]

    order = Order(
        order_number=_generate_order_number(db),
        user_id=current_user.id,
        total_amount=final_total,
        coins_applied=coins_applied,
        referral_discount=referral_discount,
        shipping_name=data.shipping_name,
        shipping_phone=data.shipping_phone,
        shipping_address=data.shipping_address,
        shipping_city=data.shipping_city,
        shipping_state=data.shipping_state,
        shipping_pincode=data.shipping_pincode,
        notes=data.notes,
        taxable_amount=round(taxable_total, 2),
        cgst_amount=round(cgst_total, 2),
        sgst_amount=round(sgst_total, 2),
        igst_amount=round(igst_total, 2),
    )
    db.add(order)
    db.flush()

    for item, unit_price, item_total, discount, hsn_code, gst_rate, area_info in items_to_create:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=unit_price,
            total_price=item_total,
            discount_applied=discount,
            hsn_code=hsn_code,
            gst_rate=gst_rate,
            dimension_length=area_info["length"] if area_info else None,
            dimension_breadth=area_info["breadth"] if area_info else None,
            computed_area=area_info["area"] if area_info else None,
            area_rate=area_info["rate"] if area_info else None,
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


@router.get("/by-number/{order_number}", response_model=OrderOut)
def get_order_by_number(order_number: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Lookup an order by its public order_number (e.g. CB-A7K9M2P4)."""
    order = db.query(Order).filter(Order.order_number == order_number.upper()).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _enrich_order(order, db)


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
    # Refund Clay Coins if any were applied
    if order.coins_applied and order.coins_applied > 0:
        wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).with_for_update().first()
        if wallet:
            wallet.balance += order.coins_applied
            db.add(WalletTransaction(
                wallet_id=wallet.id,
                amount=order.coins_applied,
                type="CREDIT",
                source="REFUND",
                description=f"Refund: order cancelled (Order #{order.order_number})",
            ))
    db.commit()
    db.refresh(order)
    return _enrich_order(order, db)


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: permanently delete an order and all its items/tracking."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    db.delete(order)
    db.commit()
    return {"detail": "Order deleted"}


# ── Invoice generation ────────────────────────────────────────

def _build_items_detail(order: Order, db: Session) -> List[dict]:
    """Build the items_detail list used by PDF generator."""
    items = []
    for oi in order.items:
        product = db.query(Product).filter(Product.id == oi.product_id).first()
        variant_label = ""
        if oi.variant_id:
            variant = db.query(ProductVariant).filter(ProductVariant.id == oi.variant_id).first()
            if variant:
                variant_label = f"{variant.variant_type}: {variant.variant_value}"
        items.append({
            "product_name": product.name if product else f"Product #{oi.product_id}",
            "variant_label": variant_label,
            "quantity": oi.quantity,
            "unit_price": oi.unit_price,
            "total_price": oi.total_price,
            "hsn_code": oi.hsn_code or "",
            "gst_rate": oi.gst_rate or 0,
            "dimension_length": oi.dimension_length,
            "dimension_breadth": oi.dimension_breadth,
            "computed_area": oi.computed_area,
            "area_rate": oi.area_rate,
        })
    return items


@router.get("/{order_id}/invoice")
def download_invoice(order_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Download the GST invoice PDF for an order.
    Customer can download their own; admin can download any."""
    from app.core.pdf_generator import generate_order_pdf

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        raise HTTPException(404, "Order's user not found")

    items_detail = _build_items_detail(order, db)
    try:
        pdf_bytes = generate_order_pdf(order, user, items_detail)
    except Exception as e:
        raise HTTPException(500, f"Invoice generation failed: {e}")

    order_num = order.order_number or f"CB-{order.id}"
    filename = f"ClayBag-Invoice-{order_num}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{order_id}/resend-invoice")
def resend_invoice_email(order_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: re-send the order confirmation + invoice email to the customer."""
    from app.core.email import send_order_confirmation
    import threading

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    user = db.query(User).filter(User.id == order.user_id).first()
    if not user or not user.email:
        raise HTTPException(404, "Order's user has no email")

    items_detail = _build_items_detail(order, db)

    # Fire-and-forget: don't block admin response
    threading.Thread(
        target=send_order_confirmation,
        args=(order, user, items_detail),
        daemon=True,
    ).start()

    return {"detail": f"Invoice email queued for {user.email}"}
