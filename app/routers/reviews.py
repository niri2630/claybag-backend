from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.review import Review
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.review import ReviewCreate, ReviewOut
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/reviews", tags=["reviews"])


def review_to_out(r: Review) -> ReviewOut:
    return ReviewOut(
        id=r.id,
        user_id=r.user_id,
        product_id=r.product_id,
        rating=r.rating,
        comment=r.comment,
        is_approved=r.is_approved,
        created_at=r.created_at,
        user_name=r.user.name if r.user else "",
        product_name=r.product.name if r.product else "",
    )


@router.post("", response_model=ReviewOut)
def create_review(data: ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(400, "Rating must be between 1 and 5")
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    # Verify user has purchased this product (confirmed or later status)
    purchased = db.query(OrderItem).join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == data.product_id,
        Order.status.in_([
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]),
    ).first()
    if not purchased:
        raise HTTPException(403, "You can only review products you have purchased.")
    # Check if user already reviewed this product
    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.product_id == data.product_id
    ).first()
    if existing:
        raise HTTPException(400, "You have already reviewed this product")
    review = Review(
        user_id=current_user.id,
        product_id=data.product_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review_to_out(review)


@router.get("/can-review/{product_id}")
def can_review(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Check if current user is eligible to review this product (has purchased it)."""
    purchased = db.query(OrderItem).join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product_id,
        Order.status.in_([
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]),
    ).first()
    already = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.product_id == product_id,
    ).first()
    return {
        "can_review": bool(purchased) and not already,
        "has_purchased": bool(purchased),
        "already_reviewed": bool(already),
    }


@router.get("/my/{product_id}", response_model=Optional[ReviewOut])
def get_my_review(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Check if current user has already reviewed this product."""
    review = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.product_id == product_id
    ).first()
    if not review:
        return None
    return review_to_out(review)


@router.get("/product/{product_id}", response_model=List[ReviewOut])
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    """Get approved reviews for a product (public)."""
    reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).order_by(Review.created_at.desc()).all()
    return [review_to_out(r) for r in reviews]


@router.get("/all", response_model=List[ReviewOut])
def get_all_reviews(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: get all reviews (approved and pending)."""
    reviews = db.query(Review).order_by(Review.created_at.desc()).all()
    return [review_to_out(r) for r in reviews]


@router.put("/{review_id}/approve", response_model=ReviewOut)
def approve_review(review_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(404, "Review not found")
    review.is_approved = True
    db.commit()
    db.refresh(review)
    return review_to_out(review)


@router.put("/{review_id}/reject", response_model=ReviewOut)
def reject_review(review_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(404, "Review not found")
    review.is_approved = False
    db.commit()
    db.refresh(review)
    return review_to_out(review)


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(404, "Review not found")
    db.delete(review)
    db.commit()
    return {"detail": "Deleted"}
