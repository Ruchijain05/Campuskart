from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.payouts import (
    AdminPayoutDashboardRead,
    AdminPayoutRead,
    PayoutCreate,
    PayoutUpdate,
    SellerPayoutHistoryRead,
)
from app.services import payouts as payout_service


seller_router = APIRouter(prefix="/seller/payouts", tags=["seller payouts"])
admin_router = APIRouter(prefix="/admin/payouts", tags=["admin payouts"])


@seller_router.get("", response_model=SellerPayoutHistoryRead)
def get_seller_payouts(
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> dict:
    return payout_service.seller_payout_history(db, seller.id)


@admin_router.get("", response_model=AdminPayoutDashboardRead)
def get_admin_payouts(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminPayoutDashboardRead:
    return payout_service.admin_payout_dashboard(db)


@admin_router.post("", response_model=AdminPayoutRead, status_code=status.HTTP_201_CREATED)
def create_admin_payout(
    details: PayoutCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminPayoutRead:
    payout = payout_service.create_payout(db, details)
    seller = db.get(User, payout.seller_id)
    return AdminPayoutRead.model_validate({
        **{field: getattr(payout, field) for field in ("id", "seller_id", "amount", "status", "reference", "note", "created_at", "updated_at", "paid_at")},
        "seller_name": seller.full_name,
        "seller_email": seller.email,
    })


@admin_router.patch("/{payout_id}", response_model=AdminPayoutRead)
def update_admin_payout(
    payout_id: int,
    details: PayoutUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminPayoutRead:
    payout = payout_service.update_payout(db, payout_id, details)
    seller = db.get(User, payout.seller_id)
    return AdminPayoutRead.model_validate({
        **{field: getattr(payout, field) for field in ("id", "seller_id", "amount", "status", "reference", "note", "created_at", "updated_at", "paid_at")},
        "seller_name": seller.full_name,
        "seller_email": seller.email,
    })
