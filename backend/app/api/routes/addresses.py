from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.addresses import AddressCreate, AddressRead, AddressUpdate
from app.services import addresses as address_service

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressRead])
def list_addresses(db: Session = Depends(get_db), buyer: User = Depends(require_roles(UserRole.BUYER))) -> list[AddressRead]:
    return address_service.list_addresses(db, buyer.id)


@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(address_in: AddressCreate, db: Session = Depends(get_db), buyer: User = Depends(require_roles(UserRole.BUYER))) -> AddressRead:
    return address_service.create_address(db, buyer.id, address_in)


@router.patch("/{address_id}", response_model=AddressRead)
def update_address(address_id: int, address_in: AddressUpdate, db: Session = Depends(get_db), buyer: User = Depends(require_roles(UserRole.BUYER))) -> AddressRead:
    return address_service.update_address(db, buyer.id, address_id, address_in)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: int, db: Session = Depends(get_db), buyer: User = Depends(require_roles(UserRole.BUYER))) -> Response:
    address_service.delete_address(db, buyer.id, address_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
