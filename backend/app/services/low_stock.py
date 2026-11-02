from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.product import Product
from app.services.notifications import create_notification


def update_low_stock_alert_state(db: Session, product: Product) -> None:
    if product.seller_id is None:
        return
    if product.stock > product.low_stock_threshold:
        product.low_stock_alert_active = False
        return
    if product.low_stock_alert_active:
        return

    create_notification(
        db,
        user_id=product.seller_id,
        kind="low_stock",
        title="Low stock alert",
        message=f"{product.name} has {product.stock} left (low-stock threshold: {product.low_stock_threshold}).",
        link="/seller/products",
    )
    product.low_stock_alert_active = True


def list_low_stock_products(db: Session, seller_id: int | None = None) -> list[dict[str, object]]:
    query = (
        select(Product, User.full_name)
        .outerjoin(User, User.id == Product.seller_id)
        .where(
            Product.is_active.is_(True),
            Product.seller_id.is_not(None),
            Product.stock <= Product.low_stock_threshold,
        )
    )
    if seller_id is not None:
        query = query.where(Product.seller_id == seller_id)
    rows = db.execute(query.order_by(Product.stock.asc(), Product.name.asc())).all()
    return [
        {
            "id": product.id,
            "name": product.name,
            "stock": product.stock,
            "low_stock_threshold": product.low_stock_threshold,
            "seller_id": product.seller_id,
            "seller_name": seller_name,
            "image_url": product.image_url,
        }
        for product, seller_name in rows
    ]
