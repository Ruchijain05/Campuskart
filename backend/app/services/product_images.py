from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.product import Product
from app.models.product_image import ProductImage


MAX_PRODUCT_IMAGES = 8
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_SIGNATURES = (
    ("image/jpeg", ".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ("image/png", ".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ("image/webp", ".webp", lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
)


def get_media_root() -> Path:
    root = Path(settings.media_root)
    return root if root.is_absolute() else Path(__file__).resolve().parents[2] / root


def _image_type(data: bytes) -> tuple[str, str]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Each image must be 5 MB or smaller")
    for content_type, extension, matches in IMAGE_SIGNATURES:
        if matches(data):
            return content_type, extension
    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP image")


def _owned_product(db: Session, product_id: int, seller_id: int) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.seller_id == seller_id).with_for_update()
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _product_rows(db: Session, product_id: int) -> list[ProductImage]:
    return list(db.scalars(
        select(ProductImage).where(ProductImage.product_id == product_id)
        .order_by(ProductImage.is_primary.desc(), ProductImage.id.asc())
    ).all())


def _save_file(data: bytes, extension: str) -> str:
    storage_key = f"products/{uuid4().hex}{extension}"
    path = get_media_root() / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(data)
    return storage_key


def _delete_file(storage_key: str | None) -> None:
    if not storage_key:
        return
    root = get_media_root().resolve()
    target = (root / storage_key).resolve()
    if not target.is_relative_to(root):
        return
    try:
        target.unlink(missing_ok=True)
    except OSError:
        # A stale file is harmless; keep the database change authoritative.
        pass


def _image_url(base_url: str, storage_key: str) -> str:
    normalized_key = storage_key.replace("\\", "/")
    return f"{base_url.rstrip('/')}/media/{normalized_key}"


def list_product_images(db: Session, product_id: int) -> list[ProductImage]:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _product_rows(db, product_id)


def upload_product_images(
    db: Session,
    *,
    product_id: int,
    seller_id: int,
    uploads: list[bytes],
    base_url: str,
) -> list[ProductImage]:
    if not uploads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose at least one image")
    if len(uploads) > MAX_PRODUCT_IMAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Upload at most {MAX_PRODUCT_IMAGES} images at a time")
    prepared = [(data, *_image_type(data)) for data in uploads]
    product = _owned_product(db, product_id, seller_id)
    existing = _product_rows(db, product_id)
    if len(existing) + len(prepared) > MAX_PRODUCT_IMAGES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A product can have at most {MAX_PRODUCT_IMAGES} images")

    saved_keys: list[str] = []
    try:
        if not existing and product.image_url:
            legacy = ProductImage(product_id=product.id, image_url=product.image_url, storage_key=None, is_primary=True)
            db.add(legacy)
            db.flush()
            existing.append(legacy)
        if existing and not any(image.is_primary for image in existing):
            existing[0].is_primary = True
            product.image_url = existing[0].image_url

        make_first_primary = not existing
        for index, (data, _content_type, extension) in enumerate(prepared):
            storage_key = _save_file(data, extension)
            saved_keys.append(storage_key)
            url = _image_url(base_url, storage_key)
            is_primary = make_first_primary and index == 0
            image = ProductImage(
                product_id=product.id,
                image_url=url,
                storage_key=storage_key,
                is_primary=is_primary,
            )
            db.add(image)
            if is_primary:
                product.image_url = url
        db.commit()
    except Exception:
        db.rollback()
        for key in saved_keys:
            _delete_file(key)
        raise
    return _product_rows(db, product_id)


def set_primary_image(db: Session, *, product_id: int, seller_id: int, image_id: int) -> list[ProductImage]:
    product = _owned_product(db, product_id, seller_id)
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id))
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    for row in _product_rows(db, product_id):
        row.is_primary = row.id == image_id
    product.image_url = image.image_url
    db.commit()
    return _product_rows(db, product_id)


def replace_product_image(
    db: Session,
    *,
    product_id: int,
    seller_id: int,
    image_id: int,
    data: bytes,
    base_url: str,
) -> list[ProductImage]:
    _content_type, extension = _image_type(data)
    product = _owned_product(db, product_id, seller_id)
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id))
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    old_key = image.storage_key
    new_key = _save_file(data, extension)
    image.image_url = _image_url(base_url, new_key)
    image.storage_key = new_key
    if image.is_primary:
        product.image_url = image.image_url
    try:
        db.commit()
    except Exception:
        db.rollback()
        _delete_file(new_key)
        raise
    _delete_file(old_key)
    return _product_rows(db, product_id)


def delete_product_image(db: Session, *, product_id: int, seller_id: int, image_id: int) -> list[ProductImage]:
    product = _owned_product(db, product_id, seller_id)
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id))
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    old_key = image.storage_key
    was_primary = image.is_primary
    db.delete(image)
    db.flush()
    remaining = _product_rows(db, product_id)
    if was_primary:
        for index, row in enumerate(remaining):
            row.is_primary = index == 0
        product.image_url = remaining[0].image_url if remaining else None
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    _delete_file(old_key)
    return _product_rows(db, product_id)
