import logging
import threading

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order, OrderTracking, OrderStatus
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.core.security import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


def _send_confirmation_email(order: Order, db: Session):
    """Send order confirmation email + PDF in a background thread (fire-and-forget)."""
    try:
        from app.core.email import send_order_confirmation

        user = db.query(User).filter(User.id == order.user_id).first()
        if not user or not user.email:
            return

        items_detail = []
        for oi in order.items:
            product = db.query(Product).filter(Product.id == oi.product_id).first()
            variant_label = ""
            if oi.variant_id:
                variant = db.query(ProductVariant).filter(ProductVariant.id == oi.variant_id).first()
                if variant:
                    variant_label = f"{variant.variant_type}: {variant.variant_value}"
            items_detail.append({
                "product_name": product.name if product else f"Product #{oi.product_id}",
                "variant_label": variant_label,
                "quantity": oi.quantity,
                "unit_price": oi.unit_price,
                "total_price": oi.total_price,
            })

        # Run in background thread so response isn't delayed
        thread = threading.Thread(
            target=send_order_confirmation,
            args=(order, user, items_detail),
            daemon=True,
        )
        thread.start()

    except Exception as e:
        logger.error("Failed to queue confirmation email for order %s: %s", order.id, e)

def _deduct_coins_after_payment(order: Order, db: Session):
    """Deduct Clay Coins from wallet after payment is confirmed."""
    if not order.coins_applied or order.coins_applied <= 0:
        return
    try:
        from app.models.wallet import Wallet, WalletTransaction
        wallet = db.query(Wallet).filter(Wallet.user_id == order.user_id).with_for_update().first()
        if not wallet:
            return
        wallet.balance -= order.coins_applied
        db.add(WalletTransaction(
            wallet_id=wallet.id,
            amount=order.coins_applied,
            type="DEBIT",
            source="REDEMPTION",
            description=f"Applied {order.coins_applied} Clay Coins (Order #{order.order_number})",
            reference_id=str(order.id),
        ))
        db.commit()
    except Exception as e:
        logger.error("Failed to deduct coins for order %s: %s", order.id, e)


CF_BASE = (
    "https://sandbox.cashfree.com/pg"
    if settings.CASHFREE_ENV == "sandbox"
    else "https://api.cashfree.com/pg"
)
CF_HEADERS = {
    "x-client-id": settings.CASHFREE_APP_ID,
    "x-client-secret": settings.CASHFREE_SECRET_KEY,
    "x-api-version": "2023-08-01",
    "Content-Type": "application/json",
}


@router.post("/create-session")
def create_payment_session(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a Cashfree payment session for an existing order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    if order.payment_status == "PAID":
        raise HTTPException(400, "Order already paid")

    # If we already have a valid session, return it
    if order.payment_session_id and order.cf_order_id:
        # Verify the session is still valid by checking order status
        try:
            with httpx.Client() as client:
                resp = client.get(
                    f"{CF_BASE}/orders/{order.cf_order_id}",
                    headers=CF_HEADERS,
                )
                if resp.status_code == 200:
                    cf_data = resp.json()
                    if cf_data.get("order_status") == "ACTIVE":
                        return {
                            "payment_session_id": order.payment_session_id,
                            "cf_order_id": order.cf_order_id,
                            "order_id": order.id,
                        }
        except Exception:
            pass  # Create a new session if check fails

    cf_order_id = f"claybag_{order.id}_{int(order.created_at.timestamp())}"

    payload = {
        "order_id": cf_order_id,
        "order_amount": round(order.total_amount, 2),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": f"cust_{current_user.id}",
            "customer_name": order.shipping_name,
            "customer_phone": order.shipping_phone,
            "customer_email": current_user.email,
        },
        "order_meta": {
            "return_url": f"{settings.FRONTEND_URL}/order/status?order_id={order.id}&cf_order_id={cf_order_id}",
        },
    }

    with httpx.Client() as client:
        resp = client.post(f"{CF_BASE}/orders", headers=CF_HEADERS, json=payload)

    if resp.status_code not in (200, 201):
        detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        raise HTTPException(502, f"Cashfree error: {detail}")

    cf_data = resp.json()
    session_id = cf_data.get("payment_session_id")

    order.cf_order_id = cf_order_id
    order.payment_session_id = session_id
    db.commit()

    return {
        "payment_session_id": session_id,
        "cf_order_id": cf_order_id,
        "order_id": order.id,
    }


@router.get("/verify/{order_id}")
def verify_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Verify payment status for an order by checking Cashfree."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "Access denied")
    if not order.cf_order_id:
        raise HTTPException(400, "No payment initiated for this order")

    with httpx.Client() as client:
        resp = client.get(
            f"{CF_BASE}/orders/{order.cf_order_id}/payments",
            headers=CF_HEADERS,
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Failed to fetch payment status from Cashfree")

    payments = resp.json()

    # Find the successful payment
    paid = False
    for p in payments:
        if p.get("payment_status") == "SUCCESS":
            paid = True
            break

    if paid and order.payment_status != "PAID":
        order.payment_status = "PAID"
        order.status = OrderStatus.CONFIRMED
        db.add(OrderTracking(
            order_id=order.id,
            status=OrderStatus.CONFIRMED,
            note="Payment confirmed via Cashfree",
        ))
        db.commit()
        db.refresh(order)

        # Deduct Clay Coins now that payment is confirmed
        _deduct_coins_after_payment(order, db)

        # Process referral rewards (credits referrer if first order)
        try:
            from app.routers.referrals import process_referral_rewards
            process_referral_rewards(order, db)
        except Exception as e:
            logger.error("Failed to process referral rewards for order %s: %s", order.id, e)

        # Send order confirmation email (async-safe, never raises)
        _send_confirmation_email(order, db)

    return {
        "order_id": order.id,
        "payment_status": order.payment_status or "PENDING",
        "order_status": order.status.value,
        "total_amount": order.total_amount,
    }


@router.post("/webhook")
async def cashfree_webhook(request: Request, db: Session = Depends(get_db)):
    """Cashfree sends payment notifications here."""
    body = await request.json()
    event_type = body.get("type")

    if event_type == "PAYMENT_SUCCESS_WEBHOOK":
        data = body.get("data", {})
        order_data = data.get("order", {})
        cf_order_id = order_data.get("order_id")

        if cf_order_id:
            order = db.query(Order).filter(Order.cf_order_id == cf_order_id).first()
            if order and order.payment_status != "PAID":
                order.payment_status = "PAID"
                order.status = OrderStatus.CONFIRMED
                db.add(OrderTracking(
                    order_id=order.id,
                    status=OrderStatus.CONFIRMED,
                    note="Payment confirmed via Cashfree webhook",
                ))
                db.commit()
                db.refresh(order)

                # Deduct Clay Coins now that payment is confirmed
                _deduct_coins_after_payment(order, db)

                # Process referral rewards
                try:
                    from app.routers.referrals import process_referral_rewards
                    process_referral_rewards(order, db)
                except Exception as e:
                    logger.error("Failed to process referral rewards for order %s: %s", order.id, e)

                # Send order confirmation email
                _send_confirmation_email(order, db)

    return {"status": "ok"}
