from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartLineRead, CartRead


def get_cart(db: Session, user_id: int) -> CartRead:
    items = db.scalars(
        select(CartItem)
        .options(joinedload(CartItem.product))
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.created_at, CartItem.id)
    ).all()
    lines: list[CartLineRead] = []
    total = Decimal("0.00")
    for item in items:
        product = item.product
        available = product.is_active and product.stock >= item.quantity
        line_total = (product.price * item.quantity).quantize(Decimal("0.01")) if available else Decimal("0.00")
        total += line_total
        lines.append(
            CartLineRead(
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                stock=product.stock,
                image_url=product.image_url,
                available=available,
                line_total=line_total,
            )
        )
    return CartRead(items=lines, total=total)


def _get_available_product(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id).with_for_update()
    )
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product is unavailable")
    return product


def add_item(db: Session, user_id: int, product_id: int, quantity: int) -> CartRead:
    product = _get_available_product(db, product_id)
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    updated_quantity = quantity + (item.quantity if item is not None else 0)
    if product.stock < updated_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {product.stock} item(s) are currently in stock.",
        )
    if item is None:
        item = CartItem(user_id=user_id, product_id=product_id, quantity=updated_quantity)
        db.add(item)
    else:
        item.quantity = updated_quantity
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The cart changed at the same time. Please try again.",
        ) from exc
    return get_cart(db, user_id)


def update_item(db: Session, user_id: int, product_id: int, quantity: int) -> CartRead:
    product = _get_available_product(db, product_id)
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    if quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {product.stock} item(s) are currently in stock.",
        )
    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_item(db: Session, user_id: int, product_id: int) -> CartRead:
    item = db.scalar(
        select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return get_cart(db, user_id)
