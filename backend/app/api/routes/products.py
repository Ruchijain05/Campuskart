from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from decimal import Decimal
from typing import Literal
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.models.product import Product
from app.schemas.product import (
    BulkProductImportResult,
    BulkProductRowError,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductOfferUpdate,
    ShoppingSectionSlug,
)
from app.services import products as product_service
from app.services.categories import existing_category_ids
from app.services.product_import import MAX_IMPORT_ROWS, ProductImportFormatError, parse_product_file

router = APIRouter(prefix="/products", tags=["products"])
MAX_IMPORT_FILE_BYTES = 5 * 1024 * 1024


@router.get("/admin-offers/products", response_model=list[ProductRead])
def list_offer_products(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[ProductRead]:
    return list(db.scalars(select(Product).order_by(Product.name.asc())).all())


@router.put("/admin-offers/{product_id}", response_model=ProductRead)
def set_product_offer(
    product_id: int,
    offer: ProductOfferUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.offer_discount_type = offer.discount_type
    product.offer_discount_value = offer.discount_value
    product.offer_starts_at = offer.starts_at
    product.offer_ends_at = offer.ends_at
    product.offer_is_active = offer.is_active
    db.commit()
    db.refresh(product)
    return product


@router.delete("/admin-offers/{product_id}", response_model=ProductRead)
def disable_product_offer(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.offer_is_active = False
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None, gt=0),
    include_descendants: bool = True,
    section_slug: ShoppingSectionSlug | None = None,
    search: str | None = Query(default=None, max_length=150),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=1, le=5),
    in_stock: bool = False,
    sort: Literal["newest", "price_asc", "price_desc", "popularity"] = "newest",
    db: Session = Depends(get_db),
) -> list[ProductRead]:
    if category_id is not None and product_service.get_category(db, category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Minimum price cannot exceed maximum price")
    return product_service.list_products(
        db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        include_descendants=include_descendants,
        section_slug=section_slug,
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        in_stock=in_stock,
        sort=sort,
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SELLER, UserRole.ADMIN)),
) -> ProductRead:
    if product_in.category_id is not None:
        category = product_service.get_category(db, product_in.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category does not exist",
            )
    seller_id = user.id if user.role == UserRole.SELLER else None
    return product_service.create_product(db, product_in, seller_id=seller_id)


@router.post(
    "/bulk",
    response_model=BulkProductImportResult,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SELLER, UserRole.ADMIN)),
) -> BulkProductImportResult:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a CSV or XLSX file.",
        )
    try:
        content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The upload must be 5 MB or smaller.",
        )
    try:
        rows = parse_product_file(file.filename, content)
    except ProductImportFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file must contain at least one product row.",
        )
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Files can contain at most {MAX_IMPORT_ROWS} product rows.",
        )

    errors: list[BulkProductRowError] = []
    validated_rows: list[tuple[int, ProductCreate]] = []
    for row_number, values in rows:
        payload = {
            "name": values.get("name") or "",
            "price": values.get("price") or "",
            "stock": values.get("stock") or "",
            "description": values.get("description") or None,
            "image_url": values.get("image_url") or None,
            "category_id": values.get("category_id") or None,
        }
        try:
            product_in = ProductCreate(**payload)
        except ValidationError as exc:
            for item in exc.errors():
                field = str(item["loc"][0]) if item["loc"] else "row"
                errors.append(
                    BulkProductRowError(
                        row=row_number,
                        field=field,
                        message=str(item["msg"]),
                    )
                )
            continue
        validated_rows.append((row_number, product_in))

    existing_ids = existing_category_ids(
        db,
        {
            product.category_id
            for _, product in validated_rows
            if product.category_id is not None
        },
    )
    for row_number, product in validated_rows:
        if product.category_id is not None and product.category_id not in existing_ids:
            errors.append(
                BulkProductRowError(
                    row=row_number,
                    field="category_id",
                    message=f"Category {product.category_id} does not exist.",
                )
            )

    if errors:
        errors.sort(key=lambda item: (item.row, item.field))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "No products were imported. Fix the listed rows and try again.",
                "errors": [item.model_dump() for item in errors],
            },
        )

    seller_id = user.id if user.role == UserRole.SELLER else None
    created = product_service.create_products(
        db,
        [product for _, product in validated_rows],
        seller_id=seller_id,
    )
    return BulkProductImportResult(imported_count=len(created), products=created)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
) -> ProductRead:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SELLER, UserRole.ADMIN)),
) -> ProductRead:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if user.role != UserRole.ADMIN and product.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = product_in.model_dump(exclude_unset=True)
    category_id = updates.get("category_id")
    if category_id is not None and product_service.get_category(db, category_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category does not exist",
        )

    return product_service.update_product(db, product, updates)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SELLER, UserRole.ADMIN)),
) -> Response:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if user.role != UserRole.ADMIN and product.seller_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product_service.delete_product(db, product)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
