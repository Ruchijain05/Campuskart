from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.address import DeliveryAddress
from app.models.auth import User
from app.schemas.addresses import AddressCreate, AddressUpdate


def list_addresses(db: Session, user_id: int) -> list[DeliveryAddress]:
    return list(db.scalars(
        select(DeliveryAddress).where(DeliveryAddress.user_id == user_id)
        .order_by(DeliveryAddress.is_default.desc(), DeliveryAddress.created_at.desc(), DeliveryAddress.id.desc())
    ).all())


def create_address(db: Session, user_id: int, address_in: AddressCreate) -> DeliveryAddress:
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    addresses = list(db.scalars(select(DeliveryAddress).where(DeliveryAddress.user_id == user_id)).all())
    data = address_in.model_dump()
    make_default = bool(data.pop("is_default")) or not addresses
    if make_default:
        for address in addresses:
            address.is_default = False
    address = DeliveryAddress(user_id=user_id, **data, is_default=make_default)
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def update_address(db: Session, user_id: int, address_id: int, update_in: AddressUpdate) -> DeliveryAddress:
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    address = db.scalar(select(DeliveryAddress).where(
        DeliveryAddress.id == address_id, DeliveryAddress.user_id == user_id
    ).with_for_update())
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    updates = {key: value for key, value in update_in.model_dump(exclude_unset=True).items() if value is not None}
    if updates.get("is_default") is True:
        db.query(DeliveryAddress).filter(
            DeliveryAddress.user_id == user_id, DeliveryAddress.id != address_id
        ).update({DeliveryAddress.is_default: False}, synchronize_session=False)
    for field, value in updates.items():
        setattr(address, field, value)
    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, user_id: int, address_id: int) -> None:
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    address = db.scalar(select(DeliveryAddress).where(
        DeliveryAddress.id == address_id, DeliveryAddress.user_id == user_id
    ).with_for_update())
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        replacement = db.scalar(select(DeliveryAddress).where(
            DeliveryAddress.user_id == user_id
        ).order_by(DeliveryAddress.created_at.asc(), DeliveryAddress.id.asc()).limit(1))
        if replacement is not None:
            replacement.is_default = True
    db.commit()
