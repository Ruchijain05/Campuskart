from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.cart import CartItemAdd, CartQuantityUpdate, CartRead
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead)
def read_cart(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> CartRead:
    return cart_service.get_cart(db, user.id)


@router.post("/items", response_model=CartRead)
def add_cart_item(
    item_in: CartItemAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> CartRead:
    return cart_service.add_item(db, user.id, item_in.product_id, item_in.quantity)


@router.patch("/items/{product_id}", response_model=CartRead)
def update_cart_item(
    product_id: int,
    item_in: CartQuantityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> CartRead:
    return cart_service.update_item(db, user.id, product_id, item_in.quantity)


@router.delete("/items/{product_id}", response_model=CartRead)
def remove_cart_item(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)),
) -> CartRead:
    return cart_service.remove_item(db, user.id, product_id)
