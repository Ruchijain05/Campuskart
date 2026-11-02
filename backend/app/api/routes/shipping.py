from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.shipping import ShippingSettingsRead, ShippingSettingsUpdate
from app.services import shipping as shipping_service


router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.get("/settings", response_model=ShippingSettingsRead)
def read_shipping_settings(db: Session = Depends(get_db)) -> ShippingSettingsRead:
    return shipping_service.get_settings(db)


@router.put("/settings", response_model=ShippingSettingsRead)
def update_shipping_settings(
    details: ShippingSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ShippingSettingsRead:
    return shipping_service.set_settings(db, details)
