from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.coupons import CouponCreate, CouponQuote, CouponRead, CouponUpdate, CouponValidation
from app.services import coupons as coupon_service


router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=list[CouponRead])
def list_coupons(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list:
    return coupon_service.list_coupons(db)


@router.post("", response_model=CouponRead, status_code=201)
def create_coupon(
    coupon_in: CouponCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> CouponRead:
    return coupon_service.create_coupon(db, coupon_in)


@router.patch("/{coupon_id}", response_model=CouponRead)
def update_coupon(
    coupon_id: int,
    coupon_in: CouponUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> CouponRead:
    return coupon_service.update_coupon(db, coupon_id, coupon_in)


@router.post("/validate", response_model=CouponQuote)
def validate_coupon(
    coupon_in: CouponValidation,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict:
    return coupon_service.quote_cart_coupon(db, buyer.id, coupon_in.code)
