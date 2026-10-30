from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate


def list_products(
    db: Session,
    *,
    skip: int,
    limit: int,
    category_id: int | None = None,
    include_descendants: bool = True,
) -> list[Product]:
    statement = select(Product).where(Product.is_active.is_(True))
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

    statement = statement.order_by(Product.created_at.desc()).offset(skip).limit(limit)
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
    product_data = product_in.model_dump()
    image_url = product_data.get("image_url")
    if image_url is not None:
        product_data["image_url"] = str(image_url)
    product_data["seller_id"] = seller_id
    product = Product(**product_data)
    db.add(product)
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
        product_data = product_in.model_dump()
        image_url = product_data.get("image_url")
        if image_url is not None:
            product_data["image_url"] = str(image_url)
        product_data["seller_id"] = seller_id
        products.append(Product(**product_data))

    try:
        db.add_all(products)
        db.flush()
        db.commit()
        for product in products:
            db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise
    return products


def update_product(db: Session, product: Product, updates: dict[str, Any]) -> Product:
    image_url = updates.get("image_url")
    if image_url is not None:
        updates["image_url"] = str(image_url)
    for field, value in updates.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
