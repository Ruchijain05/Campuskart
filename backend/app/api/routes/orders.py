from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.buy_again import BuyAgainProductRead
from app.schemas.orders import OrderCreate, OrderRead, OrderStatusUpdate
from app.services import orders as order_service
from app.services import buy_again as buy_again_service
from app.schemas.shipping import OrderShippingUpdate
from app.services import shipping as shipping_service
from app.models.order import Order
from app.services.invoices import generate_invoice_pdf
from app.services import pickup as pickup_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> OrderRead:
    return order_service.place_order(db, user.id, order_in)


@router.get("", response_model=list[OrderRead])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> list[OrderRead]:
    return order_service.list_orders(db, user.id)


@router.get("/admin", response_model=list[OrderRead])
def list_all_orders(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[OrderRead]:
    return order_service.list_all_orders(db)


@router.get("/buy-again", response_model=list[BuyAgainProductRead])
def list_buy_again_products(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[BuyAgainProductRead]:
    return buy_again_service.list_previous_products(db, buyer.id)


@router.get("/{order_id}/invoice")
def download_order_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> Response:
    order = db.scalar(select(Order).options(joinedload(Order.items)).where(Order.id == order_id))
    if order is None or (user.role != UserRole.ADMIN and order.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    pdf = generate_invoice_pdf(order)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="campuskart-invoice-{order.id}.pdf"'},
    )


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    update_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> OrderRead:
    return order_service.update_order_status(db, order_id, update_in)


@router.patch("/{order_id}/shipping", response_model=OrderRead)
def update_order_shipping(
    order_id: int,
    update_in: OrderShippingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> OrderRead:
    return shipping_service.update_order_shipping(db, order_id, update_in)


@router.patch("/{order_id}/pickup/ready", response_model=OrderRead)
def mark_pickup_ready(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> OrderRead:
    return pickup_service.mark_order_ready(db, order_id)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> OrderRead:
    order = order_service.get_order(db, user.id, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
