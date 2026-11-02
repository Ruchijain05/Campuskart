from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.bundles import BundleCreate, BundleOrderCreate, BundleRead, BundleUpdate
from app.schemas.orders import OrderRead
from app.services import bundles as bundle_service


router = APIRouter(prefix="/bundles", tags=["product bundles"])
admin_router = APIRouter(prefix="/admin/bundles", tags=["admin bundles"])


@router.get("", response_model=list[BundleRead])
def list_bundles(db: Session = Depends(get_db)) -> list[BundleRead]:
    return bundle_service.list_bundles(db)


@router.get("/{bundle_id}", response_model=BundleRead)
def get_bundle(bundle_id: int, db: Session = Depends(get_db)) -> BundleRead:
    bundle = bundle_service.get_bundle(db, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    return bundle


@router.post("/{bundle_id}/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def purchase_bundle(
    bundle_id: int,
    details: BundleOrderCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> OrderRead:
    return bundle_service.place_bundle_order(db, buyer.id, bundle_id, details)


@admin_router.get("", response_model=list[BundleRead])
def list_admin_bundles(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[BundleRead]:
    return bundle_service.list_bundles(db, include_inactive=True)


@admin_router.post("", response_model=BundleRead, status_code=status.HTTP_201_CREATED)
def create_bundle(
    details: BundleCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> BundleRead:
    return bundle_service.create_bundle(db, details)


@admin_router.put("/{bundle_id}", response_model=BundleRead)
def update_bundle(
    bundle_id: int,
    details: BundleUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> BundleRead:
    return bundle_service.update_bundle(db, bundle_id, details)


@admin_router.delete("/{bundle_id}", response_model=BundleRead)
def disable_bundle(
    bundle_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> BundleRead:
    return bundle_service.disable_bundle(db, bundle_id)
