from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.product import ProductRead
from app.services import recently_viewed as recently_viewed_service

router = APIRouter(prefix="/recently-viewed", tags=["recently viewed"])


@router.get("", response_model=list[ProductRead])
def list_recently_viewed_products(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductRead]:
    return recently_viewed_service.list_recently_viewed(db, buyer.id)


@router.put("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def record_recently_viewed_product(
    product_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> Response:
    recently_viewed_service.record_product_view(db, buyer.id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
