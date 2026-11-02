"""Razorpay Orders API calls and buyer payment lifecycle."""

import base64
from decimal import Decimal
import hashlib
import hmac
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.auth import User
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.coupon import Coupon
from app.models.product import Product
from app.schemas.orders import RazorpayPaymentStart
from app.services.email_notifications import send_email
from app.services.low_stock import update_low_stock_alert_state
from app.services.notifications import create_notification
from app.services.coupons import reserve_coupon
from app.services.shipping import order_shipping_values
from app.services.pickup import apply_fulfillment, active_location


def _credentials() -> tuple[str, str]:
    key_id = (settings.razorpay_key_id or "").strip()
    key_secret = settings.razorpay_key_secret.get_secret_value() if settings.razorpay_key_secret else ""
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Online payment is not configured. Contact the CampusKart administrator.")
    if not key_id.startswith("rzp_test_"):
        raise HTTPException(status_code=503, detail="Only Razorpay test-mode credentials are enabled.")
    return key_id, key_secret


def _api_call(method: str, path: str, payload: dict | None = None) -> dict:
    key_id, key_secret = _credentials()
    auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode("ascii")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"https://api.razorpay.com/v1/{path.lstrip('/')}",
        data=body,
        method=method,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError:
        raise HTTPException(status_code=502, detail="Razorpay could not process this payment request.") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="Razorpay is temporarily unavailable. Please try again.") from None


def _mark_paid(db: Session, order: Order, payment_id: str) -> Order:
    order.payment_status = "paid"
    order.razorpay_payment_id = payment_id
    for item in order.items:
        cart_item = db.scalar(select(CartItem).where(
            CartItem.user_id == order.user_id, CartItem.product_id == item.product_id,
        ).with_for_update()) if item.product_id is not None else None
        if cart_item is not None and cart_item.quantity == item.quantity:
            db.delete(cart_item)
    buyer = db.get(User, order.user_id)
    create_notification(db, user_id=order.user_id, kind="order_status", title="Order placed",
        message=f"Your order #{order.id} has been placed and paid successfully.", link=f"/orders/{order.id}")
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    if buyer is not None and buyer.email:
        items = "\n".join(f"- {line.product_name} x {line.quantity}" for line in order.items)
        send_email(buyer.email, f"CampusKart order confirmation #{order.id}",
            f"Hi {buyer.full_name},\n\nYour order #{order.id} has been paid successfully.\n\nItems:\n{items}\n\nTotal: INR {order.total}\nPayment: Razorpay (captured)\n\nYou can view your order in My Orders.")
    return order


def start_payment(db: Session, user_id: int, details: RazorpayPaymentStart) -> dict:
    key_id, _ = _credentials()
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    existing = db.scalar(select(Order.id).where(
        Order.user_id == user_id,
        Order.payment_method == "razorpay",
        Order.payment_status == "pending",
        Order.status == "placed",
    ).limit(1))
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have an online payment pending. Finish or dismiss it before starting another.")

    cart_items = db.scalars(
        select(CartItem).where(CartItem.user_id == user_id)
        .order_by(CartItem.product_id).with_for_update()
    ).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    products: dict[int, Product] = {}
    for item in cart_items:
        product = db.scalar(select(Product).where(Product.id == item.product_id)
            .with_for_update().execution_options(populate_existing=True))
        if product is None or not product.is_active:
            raise HTTPException(status_code=409, detail=f"{item.product.name} is no longer available.")
        if product.stock < item.quantity:
            raise HTTPException(status_code=409, detail=f"Only {product.stock} of {product.name} are currently in stock.")
        products[product.id] = product

    subtotal = sum((products[item.product_id].current_price * item.quantity for item in cart_items), Decimal("0.00")).quantize(Decimal("0.01"))
    coupon, discount_amount = reserve_coupon(db, details.coupon_code, subtotal)
    if details.delivery_method == "campus_pickup":
        active_location(db, details.pickup_location_id)
        shipping_fee, estimated_delivery_at = Decimal("0.00"), None
    else:
        shipping_fee, estimated_delivery_at = order_shipping_values(db)
    total = (subtotal - discount_amount + shipping_fee).quantize(Decimal("0.01"))
    amount = int(total * 100)
    if amount < 100:
        raise HTTPException(status_code=400, detail="The order total is below Razorpay's minimum payment amount.")

    gateway_order = _api_call("POST", "orders", {
        "amount": amount,
        "currency": "INR",
        "receipt": f"ck-{uuid4().hex[:32]}",
        "notes": {"buyer_id": str(user_id)},
    })
    gateway_order_id = gateway_order.get("id")
    if not isinstance(gateway_order_id, str) or not gateway_order_id:
        raise HTTPException(status_code=502, detail="Razorpay returned an invalid order reference.")

    order = Order(
        user_id=user_id, status="placed", payment_method="razorpay", payment_status="pending",
        razorpay_order_id=gateway_order_id,
        coupon_id=coupon.id if coupon else None, coupon_code=coupon.code if coupon else None,
        discount_description=f"Coupon {coupon.code}" if coupon else None,
        delivery_name=details.delivery_name, delivery_phone=details.delivery_phone,
        address_line=details.address_line, city=details.city, state=details.state,
        postal_code=details.postal_code, subtotal=subtotal,
        discount_amount=discount_amount, shipping_fee=shipping_fee,
        estimated_delivery_at=estimated_delivery_at, total=total,
    )
    apply_fulfillment(db, order, details)
    for item in cart_items:
        product = products[item.product_id]
        line_total = (product.current_price * item.quantity).quantize(Decimal("0.01"))
        order.items.append(OrderItem(product_id=product.id, product_name=product.name,
            seller_id=product.seller_id,
            unit_price=product.current_price, quantity=item.quantity, line_total=line_total))
        product.stock -= item.quantity
        update_low_stock_alert_state(db, product)

    db.add(order)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return {"key_id": key_id, "razorpay_order_id": gateway_order_id, "amount": amount, "currency": "INR", "order": order}


def verify_payment(db: Session, user_id: int, gateway_order_id: str, payment_id: str, signature: str) -> Order:
    _, secret = _credentials()
    order = db.scalar(select(Order).options(joinedload(Order.items)).where(
        Order.user_id == user_id, Order.razorpay_order_id == gateway_order_id,
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Payment order not found.")
    if order.payment_status == "paid":
        if order.razorpay_payment_id == payment_id:
            return order
        raise HTTPException(status_code=409, detail="This order has already been paid with a different payment.")
    if order.status != "placed" or order.payment_status != "pending":
        raise HTTPException(status_code=409, detail="This order is no longer awaiting payment.")

    message = f"{gateway_order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Razorpay payment signature is invalid.")

    payment = _api_call("GET", f"payments/{payment_id}")
    expected_amount = int(order.total * 100)
    if payment.get("order_id") != gateway_order_id or payment.get("amount") != expected_amount or payment.get("currency") != "INR":
        raise HTTPException(status_code=400, detail="Razorpay payment does not match this order.")
    if payment.get("status") != "captured":
        raise HTTPException(status_code=409, detail="Payment has not been captured yet. Please retry or contact support.")

    return _mark_paid(db, order, payment_id)


def cancel_pending_payment(db: Session, user_id: int, order_id: int) -> Order:
    order = db.scalar(select(Order).options(joinedload(Order.items)).where(
        Order.user_id == user_id, Order.id == order_id,
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.payment_status == "failed" and order.status == "cancelled":
        return order
    if order.payment_method != "razorpay" or order.payment_status != "pending" or order.status != "placed":
        raise HTTPException(status_code=409, detail="This order cannot be cancelled as a pending payment.")
    payments = _api_call("GET", f"orders/{order.razorpay_order_id}/payments").get("items", [])
    captured = next((payment for payment in payments if
        payment.get("status") == "captured"
        and payment.get("order_id") == order.razorpay_order_id
        and payment.get("amount") == int(order.total * 100)
        and payment.get("currency") == "INR"
        and isinstance(payment.get("id"), str)), None)
    if captured is not None:
        return _mark_paid(db, order, captured["id"])
    for item in order.items:
        if item.product_id is None:
            continue
        product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
        if product is not None:
            product.stock += item.quantity
            update_low_stock_alert_state(db, product)
    if order.coupon_id is not None:
        coupon = db.scalar(select(Coupon).where(Coupon.id == order.coupon_id).with_for_update())
        if coupon is not None:
            coupon.used_count = max(0, coupon.used_count - 1)
    order.status = "cancelled"
    order.payment_status = "failed"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order
