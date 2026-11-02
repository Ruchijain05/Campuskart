from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.review import Review
from app.models.order import Order, OrderItem
from app.models.shopping_section import ShoppingSection
from app.schemas.product import ProductCreate
from app.services.low_stock import update_low_stock_alert_state


def list_products(
    db: Session,
    *,
    skip: int,
    limit: int,
    category_id: int | None = None,
    include_descendants: bool = True,
    section_slug: str | None = None,
    search: str | None = None,
    min_price: Any | None = None,
    max_price: Any | None = None,
    min_rating: float | None = None,
    in_stock: bool = False,
    sort: str = "newest",
) -> list[Product]:
    statement = select(Product).where(Product.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(Product.name.ilike(term) | Product.description.ilike(term))
    if min_price is not None:
        statement = statement.where(Product.price >= min_price)
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    if in_stock:
        statement = statement.where(Product.stock > 0)

    ratings = None
    if min_rating is not None:
        ratings = (
            select(Review.product_id.label("product_id"), func.avg(Review.rating).label("average_rating"))
            .group_by(Review.product_id)
            .subquery()
        )
        statement = statement.join(ratings, ratings.c.product_id == Product.id)
        statement = statement.where(ratings.c.average_rating >= min_rating)
    if category_id is not None:
        category_ids = {category_id}
        if include_descendants:
            parent_by_id = {
                category_id_value: parent_id_value
                for category_id_value, parent_id_value in db.execute(
                    select(Category.id, Category.parent_id)
                )
            }
            children_by_parent: dict[int, list[int]] = {}
            for child_id, parent_id in parent_by_id.items():
                if parent_id is not None:
                    children_by_parent.setdefault(parent_id, []).append(child_id)
            pending = [category_id]
            while pending:
                current_id = pending.pop()
                for child_id in children_by_parent.get(current_id, []):
                    if child_id not in category_ids:
                        category_ids.add(child_id)
                        pending.append(child_id)
        statement = statement.where(Product.category_id.in_(category_ids))
    if section_slug is not None:
        statement = statement.where(Product.sections.any(ShoppingSection.slug == section_slug))

    if sort in {"price_asc", "price_desc"}:
        price_order = Product.price.asc() if sort == "price_asc" else Product.price.desc()
        statement = statement.order_by(price_order, Product.created_at.desc())
    elif sort == "popularity":
        popularity = (
            select(OrderItem.product_id.label("product_id"), func.sum(OrderItem.quantity).label("units_sold"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status != "cancelled", OrderItem.product_id.is_not(None))
            .group_by(OrderItem.product_id)
            .subquery()
        )
        statement = statement.outerjoin(popularity, popularity.c.product_id == Product.id)
        statement = statement.order_by(func.coalesce(popularity.c.units_sold, 0).desc(), Product.created_at.desc())
    else:
        statement = statement.order_by(Product.created_at.desc())
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_product(db: Session, product_id: int) -> Product | None:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        return None
    return product


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def create_product(
    db: Session,
    product_in: ProductCreate,
    *,
    seller_id: int | None = None,
) -> Product:
    product_data = product_in.model_dump(exclude={"section_slugs"})
    section_slugs = product_in.section_slugs
    image_url = product_data.get("image_url")
    if image_url is not None:
        product_data["image_url"] = str(image_url)
    product_data["seller_id"] = seller_id
    product = Product(**product_data)
    if section_slugs:
        product.sections = list(db.scalars(
            select(ShoppingSection).where(ShoppingSection.slug.in_(section_slugs))
        ).all())
    db.add(product)
    db.flush()
    update_low_stock_alert_state(db, product)
    if product.image_url:
        db.add(ProductImage(product_id=product.id, image_url=product.image_url, is_primary=True))
    db.commit()
    db.refresh(product)
    return product


def create_products(
    db: Session,
    products_in: list[ProductCreate],
    *,
    seller_id: int | None = None,
) -> list[Product]:
    products = []
    for product_in in products_in:
        product_data = product_in.model_dump(exclude={"section_slugs"})
        section_slugs = product_in.section_slugs
        image_url = product_data.get("image_url")
        if image_url is not None:
            product_data["image_url"] = str(image_url)
        product_data["seller_id"] = seller_id
        product = Product(**product_data)
        if section_slugs:
            product.sections = list(db.scalars(
                select(ShoppingSection).where(ShoppingSection.slug.in_(section_slugs))
            ).all())
        products.append(product)

    try:
        db.add_all(products)
        db.flush()
        for product in products:
            update_low_stock_alert_state(db, product)
        db.add_all([
            ProductImage(product_id=product.id, image_url=product.image_url, is_primary=True)
            for product in products if product.image_url
        ])
        db.commit()
        for product in products:
            db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise
    return products


def update_product(db: Session, product: Product, updates: dict[str, Any]) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product.id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if "section_slugs" in updates:
        section_slugs = updates.pop("section_slugs")
        product.sections = list(db.scalars(
            select(ShoppingSection).where(ShoppingSection.slug.in_(section_slugs))
        ).all()) if section_slugs else []
    if "image_url" in updates:
        image_url = str(updates["image_url"]) if updates["image_url"] is not None else None
        images = list(db.scalars(
            select(ProductImage).where(ProductImage.product_id == product.id)
            .order_by(ProductImage.is_primary.desc(), ProductImage.id.asc())
        ).all())
        if image_url is not None:
            for image in images:
                image.is_primary = False
            if images:
                images[0].image_url = image_url
                images[0].is_primary = True
            else:
                db.add(ProductImage(
                    product_id=product.id,
                    image_url=image_url,
                    storage_key=None,
                    is_primary=True,
                ))
        elif images:
            primary = next((image for image in images if image.is_primary), images[0])
            updates["image_url"] = primary.image_url
    for field, value in updates.items():
        setattr(product, field, value)
    if "stock" in updates or "low_stock_threshold" in updates:
        update_low_stock_alert_state(db, product)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
