from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.category import CategoryCreate, CategoryRead, CategoryTreeRead, CategoryUpdate
from app.services import categories as category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return category_service.list_categories(db)


@router.get("/tree", response_model=list[CategoryTreeRead])
def list_category_tree(db: Session = Depends(get_db)) -> list[CategoryTreeRead]:
    return category_service.list_category_tree(db)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
) -> CategoryRead:
    category = category_service.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> CategoryRead:
    if category_in.parent_id is not None and category_service.get_parent_category(
        db, category_in.parent_id
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent category does not exist",
        )
    if category_service.get_category_by_name(db, category_in.name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists",
        )
    try:
        return category_service.create_category(db, category_in)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists",
        ) from exc


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> CategoryRead:
    category = category_service.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    updates = category_in.model_dump(exclude_unset=True)
    if "name" in updates:
        existing = category_service.get_category_by_name(db, updates["name"])
        if existing is not None and existing.id != category.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists",
            )
    if "parent_id" in updates and updates["parent_id"] is not None:
        parent_id = updates["parent_id"]
        if category_service.get_parent_category(db, parent_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category does not exist",
            )
        if category_service.would_create_cycle(db, category_id, parent_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A category cannot be its own ancestor",
            )
    try:
        return category_service.update_category(db, category, updates)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists",
        ) from exc


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    category = category_service.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category_service.has_children(db, category_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move or delete child categories before deleting this category",
        )
    category_service.delete_category(db, category)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
