from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.order import Order, OrderItem
from app.schemas.orders import FulfillmentStatus, SellerOrderItemRead, SellerOrderRead
from app.services.notifications import create_notification
from app.services.email_notifications import send_email


FULFILLMENT_NEXT = {
    FulfillmentStatus.PROCESSING: FulfillmentStatus.PACKED,
    FulfillmentStatus.PACKED: FulfillmentStatus.SHIPPED,
    FulfillmentStatus.SHIPPED: FulfillmentStatus.DELIVERED,
    FulfillmentStatus.DELIVERED: None,
}


def list_seller_orders(db: Session, seller_id: int) -> list[SellerOrderRead]:
    rows = db.execute(
        select(Order, OrderItem)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(OrderItem.seller_id == seller_id)
        .order_by(Order.created_at.desc(), Order.id.desc(), OrderItem.id)
    ).all()
    grouped: dict[int, SellerOrderRead] = {}
    for order, item in rows:
        if order.id not in grouped:
            grouped[order.id] = SellerOrderRead(
                id=order.id,
                status=order.status,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                delivery_name=order.delivery_name,
                delivery_phone=order.delivery_phone,
                address_line=order.address_line,
                city=order.city,
                state=order.state,
                postal_code=order.postal_code,
                seller_subtotal=Decimal("0.00"),
                created_at=order.created_at,
                items=[],
            )
        summary = grouped[order.id]
        summary.items.append(SellerOrderItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_total=item.line_total,
            fulfillment_status=item.fulfillment_status,
        ))
        summary.seller_subtotal += item.line_total
    return list(grouped.values())


def update_item_fulfillment(
    db: Session,
    *,
    seller_id: int,
    item_id: int,
    next_status: FulfillmentStatus,
) -> SellerOrderItemRead:
    result = db.execute(
        select(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.id == item_id, OrderItem.seller_id == seller_id)
        .with_for_update()
    ).first()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    item, order = result
    if order.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled orders cannot be fulfilled")

    try:
        current = FulfillmentStatus(item.fulfillment_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item has an unsupported fulfillment status") from exc
    if next_status != current and next_status != FULFILLMENT_NEXT[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item cannot move from {current.value} to {next_status.value}.",
        )

    if next_status != current:
        item.fulfillment_status = next_status.value
        buyer = db.get(User, order.user_id)
        buyer_email = buyer.email if buyer is not None else None
        buyer_name = buyer.full_name if buyer is not None else "Buyer"
        order_id = order.id
        product_name = item.product_name
        create_notification(
            db,
            user_id=order.user_id,
            kind="order_fulfillment",
            title="Product fulfillment updated",
            message=f"{item.product_name} in order #{order.id} is now {next_status.value}.",
            link=f"/orders/{order.id}",
        )
        db.commit()
        db.refresh(item)
        if buyer_email:
            send_email(
                buyer_email,
                f"CampusKart order #{order_id} fulfillment update",
                f"Hi {buyer_name},\n\n{product_name} in your order #{order_id} is now {next_status.value}.\n\nSign in to CampusKart to view your order details.",
            )
    return SellerOrderItemRead.model_validate(item)
