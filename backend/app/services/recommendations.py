from collections import defaultdict

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.recently_viewed import RecentlyViewedProduct

RECOMMENDATION_LIMIT = 8


def _popularity_query():
    return (
        select(OrderItem.product_id.label("product_id"), func.sum(OrderItem.quantity).label("units_sold"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status != "cancelled", OrderItem.product_id.is_not(None))
        .group_by(OrderItem.product_id)
        .subquery()
    )


def popular_products(db: Session, limit: int = RECOMMENDATION_LIMIT) -> list[Product]:
    popularity = _popularity_query()
    return list(db.scalars(
        select(Product)
        .outerjoin(popularity, popularity.c.product_id == Product.id)
        .where(Product.is_active.is_(True), Product.stock > 0)
        .order_by(func.coalesce(popularity.c.units_sold, 0).desc(), Product.created_at.desc())
        .limit(limit)
    ).all())


def recommendations_for_buyer(db: Session, user_id: int) -> tuple[list[Product], list[Product], bool]:
    popular = popular_products(db)
    views = db.execute(
        select(RecentlyViewedProduct.product_id, Product.category_id)
        .join(Product, Product.id == RecentlyViewedProduct.product_id)
        .where(RecentlyViewedProduct.user_id == user_id, Product.is_active.is_(True))
        .order_by(RecentlyViewedProduct.viewed_at.desc(), RecentlyViewedProduct.id.desc())
        .limit(20)
    ).all()
    purchases = db.execute(
        select(OrderItem.product_id, Product.category_id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Order.user_id == user_id, Order.status != "cancelled", Product.is_active.is_(True))
        .order_by(Order.created_at.desc(), Order.id.desc(), OrderItem.id.desc())
        .limit(100)
    ).all()

    category_scores: dict[int, int] = defaultdict(int)
    viewed_ids: set[int] = set()
    purchased_ids: set[int] = set()
    for index, (product_id, category_id) in enumerate(views):
        viewed_ids.add(product_id)
        if category_id is not None:
            category_scores[category_id] += max(1, 3 - index // 5)
    for product_id, category_id in purchases:
        purchased_ids.add(product_id)
        if category_id is not None:
            category_scores[category_id] += 5

    is_personalized = bool(category_scores)
    if not is_personalized:
        # New buyers get a useful discovery list before we have activity to learn from.
        recommended = list(db.scalars(
            select(Product)
            .where(Product.is_active.is_(True), Product.stock > 0)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .limit(RECOMMENDATION_LIMIT)
        ).all())
        return recommended, popular, False

    popularity = _popularity_query()
    category_weight = case(category_scores, value=Product.category_id, else_=0)
    candidates = list(db.execute(
        select(Product, func.coalesce(popularity.c.units_sold, 0).label("units_sold"))
        .outerjoin(popularity, popularity.c.product_id == Product.id)
        .where(
            Product.is_active.is_(True),
            Product.stock > 0,
            Product.category_id.in_(category_scores),
            Product.id.not_in(viewed_ids | purchased_ids),
        )
        .order_by(category_weight.desc(), func.coalesce(popularity.c.units_sold, 0).desc(), Product.created_at.desc())
        .limit(500)
    ).all())
    candidates.sort(key=lambda row: (
        -category_scores[row[0].category_id], -int(row[1]), -row[0].created_at.timestamp()
    ))
    recommended = [row[0] for row in candidates[:RECOMMENDATION_LIMIT]]
    selected_ids = {product.id for product in recommended} | viewed_ids | purchased_ids
    if len(recommended) < RECOMMENDATION_LIMIT:
        for product in popular:
            if product.id not in selected_ids:
                recommended.append(product)
                selected_ids.add(product.id)
                if len(recommended) == RECOMMENDATION_LIMIT:
                    break
    return recommended, popular, True
