from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.coupon import Coupon
from app.schemas.coupons import CouponCreate, CouponUpdate


CENT = Decimal("0.01")


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def discount_for(coupon: Coupon, subtotal: Decimal) -> Decimal:
    if coupon.discount_type == "percentage":
        discount = (subtotal * coupon.discount_value / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        if coupon.maximum_discount is not None:
            discount = min(discount, coupon.maximum_discount)
    else:
        discount = coupon.discount_value
    return min(discount, subtotal).quantize(CENT)


def get_valid_coupon(db: Session, code: str, subtotal: Decimal, *, lock: bool = False) -> Coupon:
    query = select(Coupon).where(func.upper(Coupon.code) == code.upper())
    if lock:
        query = query.with_for_update()
    coupon = db.scalar(query)
    if coupon is None or not coupon.is_active:
        raise HTTPException(status_code=400, detail="That coupon is invalid or disabled.")
    now = datetime.now(timezone.utc)
    if _utc(coupon.starts_at) is not None and _utc(coupon.starts_at) > now:
        raise HTTPException(status_code=400, detail="That coupon is not active yet.")
    if _utc(coupon.ends_at) is not None and _utc(coupon.ends_at) <= now:
        raise HTTPException(status_code=400, detail="That coupon has expired.")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="That coupon has reached its usage limit.")
    if subtotal < coupon.minimum_order_amount:
        raise HTTPException(status_code=400, detail=f"Your cart must be at least INR {coupon.minimum_order_amount} to use this coupon.")
    return coupon


def quote_cart_coupon(db: Session, user_id: int, code: str) -> dict:
    items = db.scalars(select(CartItem).where(CartItem.user_id == user_id)).all()
    if not items:
        raise HTTPException(status_code=400, detail="Your cart is empty.")
    subtotal = sum((item.product.current_price * item.quantity for item in items), Decimal("0.00")).quantize(CENT)
    coupon = get_valid_coupon(db, code, subtotal)
    discount = discount_for(coupon, subtotal)
    return {
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "subtotal": subtotal,
        "discount_amount": discount,
        "total": (subtotal - discount).quantize(CENT),
    }


def reserve_coupon(db: Session, code: str | None, subtotal: Decimal) -> tuple[Coupon | None, Decimal]:
    if not code:
        return None, Decimal("0.00")
    coupon = get_valid_coupon(db, code, subtotal, lock=True)
    discount = discount_for(coupon, subtotal)
    if discount <= 0:
        raise HTTPException(status_code=400, detail="That coupon does not give a discount for this order.")
    coupon.used_count += 1
    return coupon, discount


def list_coupons(db: Session) -> list[Coupon]:
    return list(db.scalars(select(Coupon).order_by(Coupon.created_at.desc(), Coupon.id.desc())).all())


def create_coupon(db: Session, details: CouponCreate) -> Coupon:
    coupon = Coupon(**details.model_dump())
    db.add(coupon)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A coupon with that code already exists.") from exc
    db.refresh(coupon)
    return coupon


def update_coupon(db: Session, coupon_id: int, details: CouponUpdate) -> Coupon:
    coupon = db.scalar(select(Coupon).where(Coupon.id == coupon_id).with_for_update())
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found.")
    changes = details.model_dump(exclude_unset=True)
    required_fields = {"code", "discount_type", "discount_value", "minimum_order_amount", "is_active"}
    if any(field in changes and changes[field] is None for field in required_fields):
        raise HTTPException(status_code=422, detail="Coupon code, discount, minimum, and enabled state cannot be blank.")
    if "usage_limit" in changes and changes["usage_limit"] is not None and changes["usage_limit"] < coupon.used_count:
        raise HTTPException(status_code=409, detail="Usage limit cannot be lower than the number of uses already reserved.")
    values = {
        "code": changes.get("code", coupon.code),
        "discount_type": changes.get("discount_type", coupon.discount_type),
        "discount_value": changes.get("discount_value", coupon.discount_value),
        "starts_at": changes.get("starts_at", coupon.starts_at),
        "ends_at": changes.get("ends_at", coupon.ends_at),
    }
    if values["discount_type"] == "percentage" and values["discount_value"] > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100.")
    starts, ends = _utc(values["starts_at"]), _utc(values["ends_at"])
    if starts is not None and ends is not None and starts >= ends:
        raise HTTPException(status_code=422, detail="Coupon end time must be after its start time.")
    for field, value in changes.items():
        setattr(coupon, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A coupon with that code already exists.") from exc
    db.refresh(coupon)
    return coupon
