from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.product import ProductRead
from app.services import wishlist as wishlist_service

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=list[ProductRead])
def read_wishlist(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductRead]:
    return wishlist_service.list_products(db, user.id)


@router.put("/{product_id}", response_model=list[ProductRead])
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductRead]:
    return wishlist_service.add_product(db, user.id, product_id)


@router.delete("/{product_id}", response_model=list[ProductRead])
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductRead]:
    return wishlist_service.remove_product(db, user.id, product_id)
