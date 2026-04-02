from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderStatus
from app.models.category import Category
from app.core.security import get_current_admin

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    total_users = db.query(func.count(User.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.status != OrderStatus.CANCELLED
    ).scalar() or 0.0
    pending_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.PENDING).scalar()
    confirmed_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.CONFIRMED).scalar()
    total_categories = db.query(func.count(Category.id)).scalar()

    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()

    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "total_categories": total_categories,
        "recent_orders": [
            {
                "id": o.id,
                "user_id": o.user_id,
                "status": o.status,
                "total_amount": o.total_amount,
                "created_at": o.created_at,
            }
            for o in recent_orders
        ],
    }
