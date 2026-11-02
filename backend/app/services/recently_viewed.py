from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.recently_viewed import RecentlyViewedProduct

MAX_RECENTLY_VIEWED = 20


def list_recently_viewed(db: Session, user_id: int) -> list[Product]:
    records = db.scalars(
        select(RecentlyViewedProduct)
        .options(joinedload(RecentlyViewedProduct.product))
        .join(Product, Product.id == RecentlyViewedProduct.product_id)
        .where(
            RecentlyViewedProduct.user_id == user_id,
            Product.is_active.is_(True),
        )
        .order_by(RecentlyViewedProduct.viewed_at.desc(), RecentlyViewedProduct.id.desc())
        .limit(MAX_RECENTLY_VIEWED)
    ).all()
    return [record.product for record in records]


def record_product_view(db: Session, user_id: int, product_id: int) -> None:
    product = db.scalar(
        select(Product).where(Product.id == product_id).with_for_update()
    )
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product is unavailable")

    record = db.scalar(
        select(RecentlyViewedProduct).where(
            RecentlyViewedProduct.user_id == user_id,
            RecentlyViewedProduct.product_id == product_id,
        )
    )
    viewed_at = datetime.now(timezone.utc)
    if record is None:
        record = RecentlyViewedProduct(
            user_id=user_id,
            product_id=product_id,
            viewed_at=viewed_at,
        )
        db.add(record)
    else:
        record.viewed_at = viewed_at

    try:
        db.flush()
        _trim_history(db, user_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Concurrent requests from the same buyer can race to insert one product.
        existing = db.scalar(
            select(RecentlyViewedProduct).where(
                RecentlyViewedProduct.user_id == user_id,
                RecentlyViewedProduct.product_id == product_id,
            )
        )
        if existing is None:
            raise
        existing.viewed_at = datetime.now(timezone.utc)
        db.flush()
        _trim_history(db, user_id)
        db.commit()


def _trim_history(db: Session, user_id: int) -> None:
    keep_ids = select(RecentlyViewedProduct.id).where(
        RecentlyViewedProduct.user_id == user_id
    ).order_by(
        RecentlyViewedProduct.viewed_at.desc(), RecentlyViewedProduct.id.desc()
    ).limit(MAX_RECENTLY_VIEWED)
    db.execute(
        delete(RecentlyViewedProduct).where(
            RecentlyViewedProduct.user_id == user_id,
            RecentlyViewedProduct.id.not_in(keep_ids),
        )
    )
