"""Admin reports & data exports.

Endpoints:
- GET /reports/sales-summary  — JSON (revenue trends, top products, top customers)
- GET /reports/gst-summary    — JSON (CGST/SGST/IGST by state + HSN breakdown)
- GET /reports/orders.csv     — streaming CSV export
- GET /reports/gst.csv        — streaming CSV export (line-item level)
- GET /reports/products.csv   — streaming CSV export (catalog)

All endpoints are admin-only.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any, List
import csv
import io
import json

from app.database import get_db
from app.models.user import User
from app.models.product import Product, ProductImage, ProductVariant
from app.models.order import Order, OrderItem, OrderStatus
from app.models.category import SubCategory, Category
from app.core.security import get_current_admin
from app.core.config import settings

router = APIRouter(prefix="/reports", tags=["reports"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_date(s: Optional[str], default: date) -> date:
    """Parse YYYY-MM-DD string or return default. Raises 400 on bad format."""
    if not s:
        return default
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, f"Invalid date '{s}' — expected YYYY-MM-DD")


def _date_range(start: Optional[str], end: Optional[str], default_days: int = 30):
    """Return (start_dt, end_dt) as timezone-aware datetimes covering full days."""
    today = date.today()
    end_d = _parse_date(end, today)
    start_d = _parse_date(start, end_d - timedelta(days=default_days))
    if start_d > end_d:
        raise HTTPException(400, "start date must be <= end date")
    # Make inclusive of full days
    start_dt = datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_d, datetime.max.time(), tzinfo=timezone.utc)
    return start_d, end_d, start_dt, end_dt


def _revenue_statuses():
    """Statuses that represent actual paid revenue (exclude PENDING carts that never paid,
    and CANCELLED orders). Used for sales and GST reports."""
    return [
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ]


def _normalize_state(s: Optional[str]) -> str:
    """Lowercase + strip for state comparison (mirrors orders.py helper)."""
    return (s or "").strip().lower()


def _stream_csv(rows_iter, headers: List[str], filename: str) -> StreamingResponse:
    """Return a StreamingResponse that streams CSV rows row-by-row."""
    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for row in rows_iter:
            writer.writerow(row)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Sales summary
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/sales-summary")
def sales_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> Dict[str, Any]:
    start_d, end_d, start_dt, end_dt = _date_range(start, end)

    base_q = db.query(Order).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.status.in_(_revenue_statuses()),
    )

    total_revenue = base_q.with_entities(func.sum(Order.total_amount)).scalar() or 0.0
    order_count = base_q.count()
    avg_order_value = (total_revenue / order_count) if order_count else 0.0

    # Daily revenue buckets
    daily_rows = (
        base_q.with_entities(
            func.date(Order.created_at).label("day"),
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )
    daily_revenue = [
        {"date": str(r.day), "revenue": round(float(r.revenue or 0), 2), "orders": int(r.orders)}
        for r in daily_rows
    ]

    # Top products by revenue (join order items)
    top_products_q = (
        db.query(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label("units"),
            func.sum(OrderItem.total_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(_revenue_statuses()),
        )
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(10)
        .all()
    )
    top_products = [
        {"id": r.id, "name": r.name, "units_sold": int(r.units or 0), "revenue": round(float(r.revenue or 0), 2)}
        for r in top_products_q
    ]

    # Top customers by spend
    top_customers_q = (
        db.query(
            User.id,
            User.name,
            User.email,
            func.count(Order.id).label("orders"),
            func.sum(Order.total_amount).label("spent"),
        )
        .join(Order, Order.user_id == User.id)
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(_revenue_statuses()),
        )
        .group_by(User.id, User.name, User.email)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(10)
        .all()
    )
    top_customers = [
        {"id": r.id, "name": r.name, "email": r.email, "orders": int(r.orders), "spent": round(float(r.spent or 0), 2)}
        for r in top_customers_q
    ]

    return {
        "start": str(start_d),
        "end": str(end_d),
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": round(avg_order_value, 2),
        "daily_revenue": daily_revenue,
        "top_products": top_products,
        "top_customers": top_customers,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GST summary
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/gst-summary")
def gst_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> Dict[str, Any]:
    start_d, end_d, start_dt, end_dt = _date_range(start, end)

    orders = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(_revenue_statuses()),
        )
        .all()
    )

    total_taxable = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_igst = 0.0
    by_state: Dict[str, Dict[str, float]] = {}
    by_hsn: Dict[str, Dict[str, Any]] = {}

    for o in orders:
        taxable = float(o.taxable_amount or 0.0)
        cgst = float(o.cgst_amount or 0.0)
        sgst = float(o.sgst_amount or 0.0)
        igst = float(o.igst_amount or 0.0)
        total_taxable += taxable
        total_cgst += cgst
        total_sgst += sgst
        total_igst += igst

        state_key = (o.shipping_state or "Unknown").strip().title() or "Unknown"
        s = by_state.setdefault(state_key, {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "orders": 0})
        s["taxable"] += taxable
        s["cgst"] += cgst
        s["sgst"] += sgst
        s["igst"] += igst
        s["orders"] += 1

        # HSN breakdown via order items
        for item in o.items:
            hsn = (item.hsn_code or (item.product.hsn_code if item.product else None) or "Unclassified").strip()
            rate = float(item.gst_rate or (item.product.gst_rate if item.product else 0) or 0)
            # Back-calculate taxable for this line (inclusive pricing)
            item_gross = float(item.total_price or 0)
            item_taxable = round(item_gross / (1 + rate / 100.0), 2) if rate > 0 else item_gross
            item_tax = round(item_gross - item_taxable, 2)
            h = by_hsn.setdefault(hsn, {"hsn": hsn, "rate": rate, "taxable": 0.0, "tax": 0.0, "units": 0})
            h["taxable"] += item_taxable
            h["tax"] += item_tax
            h["units"] += int(item.quantity or 0)

    by_state_list = [
        {"state": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}}
        for k, v in sorted(by_state.items(), key=lambda kv: -kv[1]["taxable"])
    ]
    by_hsn_list = [
        {**v, "taxable": round(v["taxable"], 2), "tax": round(v["tax"], 2)}
        for v in sorted(by_hsn.values(), key=lambda x: -x["taxable"])
    ]

    return {
        "start": str(start_d),
        "end": str(end_d),
        "total_taxable": round(total_taxable, 2),
        "total_cgst": round(total_cgst, 2),
        "total_sgst": round(total_sgst, 2),
        "total_igst": round(total_igst, 2),
        "by_state": by_state_list,
        "by_hsn": by_hsn_list,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Orders CSV
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/orders.csv")
def orders_csv(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> StreamingResponse:
    start_d, end_d, start_dt, end_dt = _date_range(start, end, default_days=90)

    q = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
        .filter(Order.created_at >= start_dt, Order.created_at <= end_dt)
    )
    if status:
        # Allow only valid statuses; silently ignore bad value
        try:
            q = q.filter(Order.status == OrderStatus(status))
        except ValueError:
            raise HTTPException(400, f"Invalid status '{status}'")
    orders = q.order_by(Order.created_at.desc()).all()

    headers = [
        "order_number", "order_id", "created_at", "status",
        "customer_name", "customer_email", "customer_phone",
        "shipping_address", "shipping_city", "shipping_state", "shipping_pincode",
        "subtotal_before_discount", "referral_discount", "coins_applied",
        "taxable_amount", "cgst", "sgst", "igst", "total_amount",
        "payment_status", "cf_order_id", "items",
    ]

    def rows():
        for o in orders:
            items_str = "; ".join(
                f"{(i.product.name if i.product else 'Deleted')} x {i.quantity} @ {i.unit_price:.2f}"
                for i in (o.items or [])
            )
            # Subtotal before discounts = sum of item totals (pre-discount, pre-coins)
            subtotal = sum((i.total_price or 0) for i in (o.items or []))
            yield [
                o.order_number or f"#{o.id}",
                o.id,
                o.created_at.isoformat() if o.created_at else "",
                (o.status.value if hasattr(o.status, "value") else str(o.status)),
                o.user.name if o.user else "",
                o.user.email if o.user else "",
                o.shipping_phone or "",
                (o.shipping_address or "").replace("\n", " "),
                o.shipping_city or "",
                o.shipping_state or "",
                o.shipping_pincode or "",
                round(subtotal, 2),
                round(float(o.referral_discount or 0), 2),
                round(float(o.coins_applied or 0), 2),
                round(float(o.taxable_amount or 0), 2),
                round(float(o.cgst_amount or 0), 2),
                round(float(o.sgst_amount or 0), 2),
                round(float(o.igst_amount or 0), 2),
                round(float(o.total_amount or 0), 2),
                o.payment_status or "",
                o.cf_order_id or "",
                items_str,
            ]

    filename = f"claybag-orders-{start_d}-to-{end_d}.csv"
    return _stream_csv(rows(), headers, filename)


# ──────────────────────────────────────────────────────────────────────────────
# GST CSV (line-item level)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/gst.csv")
def gst_csv(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> StreamingResponse:
    start_d, end_d, start_dt, end_dt = _date_range(start, end, default_days=90)

    orders = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user))
        .filter(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_(_revenue_statuses()),
        )
        .order_by(Order.created_at)
        .all()
    )

    headers = [
        "order_number", "order_date", "customer_name", "shipping_state",
        "hsn", "product_name", "quantity", "unit_price_incl",
        "line_total_incl", "gst_rate", "taxable",
        "cgst_amount", "sgst_amount", "igst_amount",
    ]

    company_state_norm = _normalize_state(settings.COMPANY_STATE)

    def rows():
        for o in orders:
            is_intra = _normalize_state(o.shipping_state) == company_state_norm
            for item in (o.items or []):
                rate = float(item.gst_rate or (item.product.gst_rate if item.product else 0) or 0)
                gross = float(item.total_price or 0)
                taxable = round(gross / (1 + rate / 100.0), 2) if rate > 0 else gross
                tax_total = round(gross - taxable, 2)
                cgst = round(tax_total / 2, 2) if is_intra else 0.0
                sgst = round(tax_total / 2, 2) if is_intra else 0.0
                igst = tax_total if not is_intra else 0.0
                yield [
                    o.order_number or f"#{o.id}",
                    o.created_at.date().isoformat() if o.created_at else "",
                    o.user.name if o.user else "",
                    o.shipping_state or "",
                    item.hsn_code or (item.product.hsn_code if item.product else ""),
                    item.product.name if item.product else "Deleted",
                    item.quantity,
                    round(float(item.unit_price or 0), 2),
                    round(gross, 2),
                    rate,
                    taxable,
                    cgst,
                    sgst,
                    igst,
                ]

    filename = f"claybag-gst-{start_d}-to-{end_d}.csv"
    return _stream_csv(rows(), headers, filename)


# ──────────────────────────────────────────────────────────────────────────────
# Products CSV (catalog)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/products.csv")
def products_csv(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
) -> StreamingResponse:
    products = (
        db.query(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.subcategory).selectinload(SubCategory.category),
        )
        .order_by(Product.id)
        .all()
    )

    headers = [
        "id", "name", "slug", "category", "subcategory",
        "base_price", "compare_price", "hsn_code", "gst_rate", "min_order_qty",
        "is_active", "is_featured", "has_variants", "variant_count", "image_count",
        "primary_image_url", "branding_methods", "created_at", "updated_at",
    ]

    def rows():
        for p in products:
            subcat_name = p.subcategory.name if p.subcategory else ""
            cat_name = (p.subcategory.category.name if (p.subcategory and p.subcategory.category) else "")
            primary = next((img.image_url for img in (p.images or []) if img.is_primary), "")
            if not primary and p.images:
                primary = p.images[0].image_url
            # Parse branding methods — stored as JSON array or plain string
            branding = ""
            if p.branding_methods:
                try:
                    parsed = json.loads(p.branding_methods)
                    branding = ", ".join(parsed) if isinstance(parsed, list) else str(parsed)
                except (ValueError, TypeError):
                    branding = p.branding_methods
            yield [
                p.id,
                p.name,
                p.slug or "",
                cat_name,
                subcat_name,
                round(float(p.base_price or 0), 2),
                round(float(p.compare_price), 2) if p.compare_price else "",
                p.hsn_code or "",
                float(p.gst_rate) if p.gst_rate is not None else "",
                p.min_order_qty or "",
                "yes" if p.is_active else "no",
                "yes" if p.is_featured else "no",
                "yes" if p.has_variants else "no",
                len(p.variants or []),
                len(p.images or []),
                primary,
                branding,
                p.created_at.isoformat() if p.created_at else "",
                p.updated_at.isoformat() if p.updated_at else "",
            ]

    today = date.today().isoformat()
    filename = f"claybag-products-{today}.csv"
    return _stream_csv(rows(), headers, filename)
