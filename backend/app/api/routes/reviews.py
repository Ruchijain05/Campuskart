from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.reviews import ReviewCreate, ReviewRead, ReviewSummary, ReviewUpdate
from app.services import reviews as review_service

router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=ReviewSummary)
def list_product_reviews(product_id: int, db: Session = Depends(get_db)) -> ReviewSummary:
    return review_service.get_product_reviews(db, product_id)


@router.get("/products/{product_id}/reviews/mine", response_model=ReviewRead | None)
def read_my_product_review(
    product_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict | None:
    review = review_service.get_my_review(db, product_id, buyer.id)
    return review_service.format_my_review(db, review)


@router.post(
    "/products/{product_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product_review(
    product_id: int,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict:
    review = review_service.create_review(db, product_id, buyer.id, review_in)
    return review_service.format_my_review(db, review) or {}


@router.patch("/reviews/{review_id}", response_model=ReviewRead)
def edit_review(
    review_id: int,
    review_in: ReviewUpdate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict:
    review = review_service.update_review(db, review_id, buyer.id, review_in)
    return review_service.format_my_review(db, review) or {}


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_review(
    review_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> Response:
    review_service.delete_review(db, review_id, buyer.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
