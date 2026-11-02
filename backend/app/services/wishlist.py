from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.wishlist import WishlistItem


def list_products(db: Session, user_id: int) -> list[Product]:
    items = db.scalars(
        select(WishlistItem)
        .options(joinedload(WishlistItem.product))
        .where(WishlistItem.user_id == user_id)
        .order_by(WishlistItem.created_at, WishlistItem.id)
    ).all()
    return [item.product for item in items]


def add_product(db: Session, user_id: int, product_id: int) -> list[Product]:
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product is unavailable")
    existing = db.scalar(
        select(WishlistItem.id).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
    )
    if existing is None:
        db.add(WishlistItem(user_id=user_id, product_id=product_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if db.scalar(select(WishlistItem.id).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )) is None:
                raise
    return list_products(db, user_id)


def remove_product(db: Session, user_id: int, product_id: int) -> list[Product]:
    item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
    )
    if item is not None:
        db.delete(item)
        db.commit()
    return list_products(db, user_id)
