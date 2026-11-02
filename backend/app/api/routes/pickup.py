from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.models.pickup_location import CampusPickupLocation
from app.schemas.pickup import PickupLocationInput, PickupLocationRead
from app.services import pickup as pickup_service

router = APIRouter(prefix="/pickup/locations", tags=["campus pickup"])


@router.get("", response_model=list[PickupLocationRead])
def get_locations(db: Session = Depends(get_db)) -> list[CampusPickupLocation]:
    return pickup_service.list_locations(db)


@router.get("/admin", response_model=list[PickupLocationRead])
def get_all_locations(db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> list[CampusPickupLocation]:
    return pickup_service.list_locations(db, include_inactive=True)


@router.post("", response_model=PickupLocationRead, status_code=201)
def create_location(details: PickupLocationInput, db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> CampusPickupLocation:
    return pickup_service.create_location(db, details)


@router.put("/{location_id}", response_model=PickupLocationRead)
def update_location(location_id: int, details: PickupLocationInput, db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> CampusPickupLocation:
    return pickup_service.update_location(db, location_id, details)


@router.delete("/{location_id}", response_model=PickupLocationRead)
def disable_location(location_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> CampusPickupLocation:
    return pickup_service.disable_location(db, location_id)
