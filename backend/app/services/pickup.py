from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.order import Order
from app.models.delivery_job import DeliveryJob
from app.models.pickup_location import CampusPickupLocation
from app.schemas.orders import OrderCreate
from app.schemas.pickup import PickupLocationInput
from app.services.email_notifications import send_email
from app.services.notifications import create_notification


def list_locations(db: Session, *, include_inactive: bool = False) -> list[CampusPickupLocation]:
    query = select(CampusPickupLocation).order_by(CampusPickupLocation.name, CampusPickupLocation.id)
    if not include_inactive:
        query = query.where(CampusPickupLocation.is_active.is_(True))
    return list(db.scalars(query).all())


def create_location(db: Session, details: PickupLocationInput) -> CampusPickupLocation:
    location = CampusPickupLocation(**details.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def update_location(db: Session, location_id: int, details: PickupLocationInput) -> CampusPickupLocation:
    location = db.get(CampusPickupLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Pickup location not found.")
    for key, value in details.model_dump().items():
        setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return location


def disable_location(db: Session, location_id: int) -> CampusPickupLocation:
    location = db.get(CampusPickupLocation, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Pickup location not found.")
    location.is_active = False
    db.commit()
    db.refresh(location)
    return location


def apply_fulfillment(db: Session, order: Order, details: OrderCreate) -> None:
    order.delivery_method = details.delivery_method
    if details.delivery_method == "home_delivery":
        order.pickup_location_id = None
        order.pickup_location_name = None
        order.pickup_status = "not_applicable"
        return
    location = active_location(db, details.pickup_location_id)
    order.pickup_location_id = location.id
    order.pickup_location_name = location.name
    order.pickup_status = "awaiting_pickup"
    order.address_line = location.address_line
    order.city = location.city
    order.state = location.state
    order.postal_code = location.postal_code
    order.shipping_fee = 0
    order.estimated_delivery_at = None


def active_location(db: Session, location_id: int | None) -> CampusPickupLocation:
    location = db.scalar(select(CampusPickupLocation).where(
        CampusPickupLocation.id == location_id,
        CampusPickupLocation.is_active.is_(True),
    )) if location_id is not None else None
    if location is None:
        raise HTTPException(status_code=409, detail="This campus pickup location is unavailable. Choose another location.")
    return location


def mark_order_ready(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.delivery_method != "campus_pickup":
        raise HTTPException(status_code=409, detail="This order is not for campus pickup.")
    assigned_job = db.scalar(select(DeliveryJob.id).where(DeliveryJob.order_id == order_id))
    if assigned_job is not None and order.pickup_status != "ready":
        raise HTTPException(status_code=409, detail="The assigned delivery person must mark this order ready at its pickup point.")
    if order.status == "cancelled":
        raise HTTPException(status_code=409, detail="A cancelled order cannot be marked ready for pickup.")
    if order.pickup_status == "ready":
        return order
    if order.pickup_status == "collected":
        raise HTTPException(status_code=409, detail="This order has already been collected.")
    order.pickup_status = "ready"
    buyer = db.get(User, order.user_id)
    create_notification(db, user_id=order.user_id, kind="order_status", title="Your campus pickup is ready",
        message=f"Order #{order.id} is ready for collection at {order.pickup_location_name or 'your selected campus location'}.",
        link=f"/orders/{order.id}")
    db.commit()
    db.refresh(order)
    if buyer and buyer.email:
        send_email(buyer.email, f"CampusKart order #{order.id} is ready for pickup",
            f"Hi {buyer.full_name},\n\nYour order #{order.id} is ready for pickup at {order.pickup_location_name}.\n\nPickup location: {order.address_line}, {order.city}, {order.state} {order.postal_code}\n\nPlease show your order details when you collect it.")
    return order
