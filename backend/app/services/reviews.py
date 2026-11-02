from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.product import Product
from app.models.review import Review
from app.schemas.reviews import ReviewCreate, ReviewSummary, ReviewUpdate


def _get_active_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _review_read(review: Review, user: User) -> dict:
    return {
        "id": review.id,
        "product_id": review.product_id,
        "reviewer_name": user.full_name.split()[0] if user.full_name.strip() else "Buyer",
        "rating": review.rating,
        "body": review.body,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def get_product_reviews(db: Session, product_id: int) -> ReviewSummary:
    _get_active_product(db, product_id)
    average, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.product_id == product_id)
    ).one()
    rows = db.execute(
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .where(Review.product_id == product_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    average_rating = Decimal(str(average)).quantize(Decimal("0.01")) if average is not None else None
    return ReviewSummary(
        average_rating=average_rating,
        review_count=count,
        reviews=[_review_read(review, user) for review, user in rows],
    )


def get_my_review(db: Session, product_id: int, user_id: int) -> Review | None:
    _get_active_product(db, product_id)
    return db.scalar(
        select(Review).where(Review.product_id == product_id, Review.user_id == user_id)
    )


def create_review(db: Session, product_id: int, user_id: int, review_in: ReviewCreate) -> Review:
    _get_active_product(db, product_id)
    review = Review(
        product_id=product_id,
        user_id=user_id,
        rating=review_in.rating,
        body=review_in.body,
    )
    db.add(review)
    try:
        db.commit()
        db.refresh(review)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this product. Edit your existing review instead.",
        ) from exc
    return review


def update_review(db: Session, review_id: int, user_id: int, review_in: ReviewUpdate) -> Review:
    review = db.scalar(select(Review).where(Review.id == review_id, Review.user_id == user_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    for field, value in review_in.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> None:
    review = db.scalar(select(Review).where(Review.id == review_id, Review.user_id == user_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    db.delete(review)
    db.commit()


def format_my_review(db: Session, review: Review | None) -> dict | None:
    if review is None:
        return None
    user = db.get(User, review.user_id)
    if user is None:
        return None
    return _review_read(review, user)
