from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.services.notifications import create_notification
from app.services.email_notifications import send_email
from app.models.auth import User
from app.models.product import Product
from app.schemas.orders import OrderCreate, OrderStatus, OrderStatusUpdate
from app.services.low_stock import update_low_stock_alert_state
from app.services.coupons import reserve_coupon
from app.services.shipping import order_shipping_values
from app.services.pickup import apply_fulfillment, active_location


ALLOWED_STATUS_TRANSITIONS = {
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def place_order(db: Session, user_id: int, details: OrderCreate) -> Order:
    cart_items = db.scalars(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.product_id)
        .with_for_update()
    ).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your cart is empty.")

    products: dict[int, Product] = {}
    for item in cart_items:
        product = db.scalar(
            select(Product).where(Product.id == item.product_id).with_for_update()
            .execution_options(populate_existing=True)
        )
        if product is None or not product.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{item.product.name} is no longer available.")
        if product.stock < item.quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Only {product.stock} of {product.name} are currently in stock.")
        products[product.id] = product

    subtotal = sum((products[item.product_id].current_price * item.quantity for item in cart_items), Decimal("0.00")).quantize(Decimal("0.01"))
    coupon, discount_amount = reserve_coupon(db, details.coupon_code, subtotal)
    if details.delivery_method == "campus_pickup":
        active_location(db, details.pickup_location_id)
        shipping_fee, estimated_delivery_at = Decimal("0.00"), None
    else:
        shipping_fee, estimated_delivery_at = order_shipping_values(db)
    total = (subtotal - discount_amount + shipping_fee).quantize(Decimal("0.01"))
    fully_discounted = total == Decimal("0.00")
    order = Order(
        user_id=user_id,
        status="placed",
        payment_method="coupon" if fully_discounted else "cod",
        payment_status="paid" if fully_discounted else "pending",
        coupon_id=coupon.id if coupon else None,
        coupon_code=coupon.code if coupon else None,
        discount_description=f"Coupon {coupon.code}" if coupon else None,
        delivery_name=details.delivery_name,
        delivery_phone=details.delivery_phone,
        address_line=details.address_line,
        city=details.city,
        state=details.state,
        postal_code=details.postal_code,
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_fee=shipping_fee,
        estimated_delivery_at=estimated_delivery_at,
        total=total,
    )
    apply_fulfillment(db, order, details)
    for item in cart_items:
        product = products[item.product_id]
        line_total = (product.current_price * item.quantity).quantize(Decimal("0.01"))
        order.items.append(OrderItem(
            product_id=product.id,
            seller_id=product.seller_id,
            product_name=product.name,
            unit_price=product.current_price,
            quantity=item.quantity,
            line_total=line_total,
        ))
        product.stock -= item.quantity
        update_low_stock_alert_state(db, product)
        db.delete(item)
    db.add(order)
    db.flush()
    buyer = db.get(User, user_id)
    buyer_email = buyer.email if buyer is not None else None
    buyer_name = buyer.full_name if buyer is not None else "Buyer"
    order_id = order.id
    order_total = order.total
    item_lines = [f"- {item.product_name} x {item.quantity}" for item in order.items]
    create_notification(
        db,
        user_id=user_id,
        kind="order_status",
        title="Order placed",
        message=f"Your order #{order.id} has been placed successfully.",
        link=f"/orders/{order.id}",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    if buyer_email:
        payment_label = "No payment due (coupon discount)" if fully_discounted else "Cash on Delivery"
        send_email(
            buyer_email,
            f"CampusKart order confirmation #{order_id}",
            f"Hi {buyer_name},\n\nYour order #{order_id} has been placed successfully.\n\nItems:\n{chr(10).join(item_lines)}\n\nTotal: INR {order_total}\nPayment: {payment_label}\n\nYou can view your order in My Orders.",
        )
    return order


def list_orders(db: Session, user_id: int) -> list[Order]:
    return list(db.scalars(
        select(Order).options(joinedload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).unique().all())


def get_order(db: Session, user_id: int, order_id: int) -> Order | None:
    return db.scalar(
        select(Order).options(joinedload(Order.items))
        .where(Order.user_id == user_id, Order.id == order_id)
    )


def list_all_orders(db: Session) -> list[Order]:
    return list(db.scalars(
        select(Order).options(joinedload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).unique().all())


def update_order_status(
    db: Session,
    order_id: int,
    update_in: OrderStatusUpdate,
) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    try:
        current = OrderStatus(order.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order has an unsupported status and cannot be updated.",
        ) from exc
    next_status = update_in.status
    if order.delivery_method == "campus_pickup" and next_status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campus pickup delivery progress is managed through the assigned staff job.",
        )
    if order.payment_method == "razorpay" and order.payment_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A Razorpay order cannot be changed until its payment is verified or cancelled through checkout.",
        )
    if next_status not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order cannot move from {current.value} to {next_status.value}.",
        )

    if next_status == OrderStatus.CANCELLED:
        for item in order.items:
            if item.product_id is None:
                continue
            product = db.scalar(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            if product is not None:
                product.stock += item.quantity
                update_low_stock_alert_state(db, product)
        if order.payment_method == "razorpay" and order.payment_status == "pending":
            order.payment_status = "failed"

    order.status = next_status.value
    buyer = db.get(User, order.user_id)
    buyer_email = buyer.email if buyer is not None else None
    buyer_name = buyer.full_name if buyer is not None else "Buyer"
    order_id = order.id
    create_notification(
        db,
        user_id=order.user_id,
        kind="order_status",
        title="Order status updated",
        message=f"Your order #{order.id} is now {next_status.value}.",
        link=f"/orders/{order.id}",
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    if buyer_email:
        send_email(
            buyer_email,
            f"CampusKart order #{order_id} status update",
            f"Hi {buyer_name},\n\nThe status of your order #{order_id} is now {next_status.value}.\n\nSign in to CampusKart to view your order details.",
        )
    return order
