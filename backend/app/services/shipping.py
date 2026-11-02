from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.shipping_settings import ShippingSettings
from app.schemas.shipping import OrderShippingUpdate, ShippingSettingsUpdate
from app.models.auth import User
from app.services.email_notifications import send_email
from app.services.notifications import create_notification


def get_settings(db: Session) -> dict:
    settings = db.get(ShippingSettings, 1)
    if settings is None:
        return {"id": 1, "delivery_charge": Decimal("0.00"), "estimated_delivery_days": 5, "updated_at": None}
    return {
        "id": settings.id,
        "delivery_charge": settings.delivery_charge,
        "estimated_delivery_days": settings.estimated_delivery_days,
        "updated_at": settings.updated_at,
    }


def set_settings(db: Session, details: ShippingSettingsUpdate) -> ShippingSettings:
    settings = db.get(ShippingSettings, 1)
    if settings is None:
        settings = ShippingSettings(id=1)
        db.add(settings)
    settings.delivery_charge = details.delivery_charge
    settings.estimated_delivery_days = details.estimated_delivery_days
    db.commit()
    db.refresh(settings)
    return settings


def order_shipping_values(db: Session) -> tuple[Decimal, datetime]:
    settings = get_settings(db)
    days = settings["estimated_delivery_days"]
    return settings["delivery_charge"], datetime.now(timezone.utc) + timedelta(days=days)


def update_order_shipping(db: Session, order_id: int, details: OrderShippingUpdate) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    estimated = details.estimated_delivery_at
    if estimated is not None:
        estimated = estimated.replace(tzinfo=timezone.utc) if estimated.tzinfo is None else estimated.astimezone(timezone.utc)
    previous_estimate = order.estimated_delivery_at
    if previous_estimate is not None:
        previous_estimate = previous_estimate.replace(tzinfo=timezone.utc) if previous_estimate.tzinfo is None else previous_estimate.astimezone(timezone.utc)
    changed = (previous_estimate != estimated or order.courier_name != details.courier_name or order.tracking_id != details.tracking_id)
    order.estimated_delivery_at = estimated
    order.courier_name = details.courier_name
    order.tracking_id = details.tracking_id
    buyer = db.get(User, order.user_id) if changed else None
    if changed:
        create_notification(
            db,
            user_id=order.user_id,
            kind="order_status",
            title="Delivery details updated",
            message=f"Shipping details for your order #{order.id} have been updated.",
            link=f"/orders/{order.id}",
        )
    db.commit()
    db.refresh(order)
    if buyer is not None and buyer.email:
        send_email(
            buyer.email,
            f"CampusKart order #{order.id} delivery update",
            f"Hi {buyer.full_name},\n\nDelivery details for your order #{order.id} have been updated. Sign in to CampusKart to view the latest estimate and tracking information.",
        )
    return order
