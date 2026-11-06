from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.auth import (
    SellerApplicationCreate,
    SellerApplicationRead,
    SellerApplicationReview,
    UserRead,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return user


@router.post(
    "/seller-applications",
    response_model=SellerApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_become_seller(
    application_in: SellerApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER)),
) -> SellerApplicationRead:
    try:
        return auth_service.create_seller_application(db, user, application_in)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A seller application already exists",
        ) from exc


@router.get(
    "/seller-applications",
    response_model=list[SellerApplicationRead],
)
def list_seller_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[SellerApplicationRead]:
    return auth_service.list_seller_applications(db)


@router.patch(
    "/seller-applications/{application_id}",
    response_model=SellerApplicationRead,
)
def review_seller_application(
    application_id: int,
    review: SellerApplicationReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> SellerApplicationRead:
    return auth_service.review_seller_application(
        db,
        application_id=application_id,
        admin=admin,
        decision=review.decision.value,
        review_note=review.review_note,
    )
