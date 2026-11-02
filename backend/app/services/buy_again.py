from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.buy_again import BuyAgainProductRead


def list_previous_products(db: Session, user_id: int) -> list[BuyAgainProductRead]:
    rows = db.execute(
        select(OrderItem, Order.created_at, Product)
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc(), OrderItem.id.desc())
    ).all()

    latest_by_product: dict[tuple[int | None, str], BuyAgainProductRead] = {}
    for item, ordered_at, product in rows:
        key = (item.product_id, "" if item.product_id is not None else item.product_name)
        if key in latest_by_product:
            continue
        available = product is not None and product.is_active and product.stock > 0
        if product is None or not product.is_active:
            unavailable_reason = "No longer available"
        elif product.stock < 1:
            unavailable_reason = "Out of stock"
        else:
            unavailable_reason = None
        latest_by_product[key] = BuyAgainProductRead(
            product_id=item.product_id,
            product_name=product.name if product is not None else item.product_name,
            price=(product.price if available else item.unit_price) or Decimal("0.00"),
            image_url=product.image_url if product is not None else None,
            stock=product.stock if product is not None and product.is_active else 0,
            available=available,
            unavailable_reason=unavailable_reason,
            last_ordered_at=ordered_at,
            last_quantity=item.quantity,
        )
    return list(latest_by_product.values())
