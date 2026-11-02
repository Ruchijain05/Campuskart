from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.product_requests import AdminProductRequestRead, ProductRequestRead, ProductRequestResponse
from app.services import product_requests as request_service

buyer_router = APIRouter(prefix="/product-requests", tags=["product requests"])
admin_router = APIRouter(prefix="/admin/product-requests", tags=["product requests"])


@buyer_router.post("", response_model=ProductRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
    request: Request,
    product_name: str = Form(..., min_length=1, max_length=160),
    quantity: int = Form(..., ge=1, le=100000),
    message: str = Form(..., min_length=1, max_length=5000),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> ProductRequestRead:
    return await request_service.create_request(
        db,
        buyer,
        product_name=product_name,
        quantity=quantity,
        message=message,
        photo=photo,
        base_url=str(request.base_url),
    )


@buyer_router.get("", response_model=list[ProductRequestRead])
def list_my_requests(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ProductRequestRead]:
    return request_service.list_buyer_requests(db, buyer.id)


@admin_router.get("", response_model=list[AdminProductRequestRead])
def list_all_requests(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[AdminProductRequestRead]:
    return request_service.list_admin_requests(db)


@admin_router.patch("/{request_id}/response", response_model=AdminProductRequestRead)
def respond_to_request(
    request_id: int,
    response: ProductRequestResponse,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminProductRequestRead:
    return request_service.respond_to_request(db, request_id, response)
