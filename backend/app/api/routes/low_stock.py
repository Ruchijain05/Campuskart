from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.low_stock import LowStockProductRead
from app.services.low_stock import list_low_stock_products

seller_router = APIRouter(prefix="/seller/low-stock", tags=["low stock"])
admin_router = APIRouter(prefix="/admin/low-stock", tags=["low stock"])


@seller_router.get("", response_model=list[LowStockProductRead])
def seller_low_stock(
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[LowStockProductRead]:
    return list_low_stock_products(db, seller.id)


@admin_router.get("", response_model=list[LowStockProductRead])
def admin_low_stock(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[LowStockProductRead]:
    return list_low_stock_products(db)
