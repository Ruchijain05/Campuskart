from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.seller_dashboard import SellerDashboardRead
from app.services.seller_dashboard import get_seller_dashboard

router = APIRouter(prefix="/seller/dashboard", tags=["seller dashboard"])


@router.get("", response_model=SellerDashboardRead)
def read_seller_dashboard(
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> SellerDashboardRead:
    return get_seller_dashboard(db, seller.id)
