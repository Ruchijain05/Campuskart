from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryTreeRead


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


def list_category_tree(db: Session) -> list[CategoryTreeRead]:
    categories = list_categories(db)
    children_by_parent: dict[int | None, list[Category]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_id, []).append(category)

    def build_children(parent_id: int | None) -> list[CategoryTreeRead]:
        return [
            CategoryTreeRead(
                id=child.id,
                name=child.name,
                description=child.description,
                parent_id=child.parent_id,
                children=build_children(child.id),
            )
            for child in children_by_parent.get(parent_id, [])
        ]

    return build_children(None)


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_category_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == name))


def get_parent_category(db: Session, parent_id: int) -> Category | None:
    return db.get(Category, parent_id)


def existing_category_ids(db: Session, category_ids: set[int]) -> set[int]:
    if not category_ids:
        return set()
    return set(
        db.scalars(select(Category.id).where(Category.id.in_(category_ids))).all()
    )


def has_children(db: Session, category_id: int) -> bool:
    return db.scalar(
        select(Category.id).where(Category.parent_id == category_id).limit(1)
    ) is not None


def would_create_cycle(db: Session, category_id: int, parent_id: int) -> bool:
    parent_by_id = {
        category_id_value: parent_id_value
        for category_id_value, parent_id_value in db.execute(
            select(Category.id, Category.parent_id)
        )
    }
    visited: set[int] = set()
    current_id: int | None = parent_id
    while current_id is not None:
        if current_id == category_id:
            return True
        if current_id in visited:
            return True
        visited.add(current_id)
        current_id = parent_by_id.get(current_id)
    return False


def create_category(db: Session, category_in: CategoryCreate) -> Category:
    category = Category(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category: Category,
    updates: dict[str, str | int | None],
) -> Category:
    for field, value in updates.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
