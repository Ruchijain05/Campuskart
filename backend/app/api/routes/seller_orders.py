from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.orders import FulfillmentStatusUpdate, SellerOrderItemRead, SellerOrderRead
from app.services import seller_orders as seller_order_service

router = APIRouter(prefix="/seller/orders", tags=["seller orders"])


@router.get("", response_model=list[SellerOrderRead])
def list_orders(
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[SellerOrderRead]:
    return seller_order_service.list_seller_orders(db, seller.id)


@router.patch("/items/{item_id}/fulfillment", response_model=SellerOrderItemRead)
def update_fulfillment(
    item_id: int,
    update_in: FulfillmentStatusUpdate,
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> SellerOrderItemRead:
    return seller_order_service.update_item_fulfillment(
        db,
        seller_id=seller.id,
        item_id=item_id,
        next_status=update_in.status,
    )
