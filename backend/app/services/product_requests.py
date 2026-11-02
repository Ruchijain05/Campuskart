from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.auth import User
from app.models.product_request import ProductRequest
from app.schemas.product_requests import ProductRequestResponse
from app.services.notifications import create_notification


MAX_PHOTO_BYTES = 5 * 1024 * 1024
IMAGE_SIGNATURES = (
    (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    (".webp", lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
)


def _media_root() -> Path:
    root = Path(settings.media_root)
    return root if root.is_absolute() else Path(__file__).resolve().parents[2] / root


async def _save_photo(photo: UploadFile | None, base_url: str) -> tuple[str | None, Path | None]:
    if photo is None:
        return None, None
    try:
        data = await photo.read(MAX_PHOTO_BYTES + 1)
    finally:
        await photo.close()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The photo file is empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The photo must be 5 MB or smaller")
    extension = next((ext for ext, matches in IMAGE_SIGNATURES if matches(data)), None)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a JPEG, PNG, or WebP photo")

    storage_key = f"product-requests/{uuid4().hex}{extension}"
    path = _media_root() / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(data)
    return f"{base_url.rstrip('/')}/media/{storage_key}", path


async def create_request(
    db: Session,
    buyer: User,
    *,
    product_name: str,
    quantity: int,
    message: str,
    photo: UploadFile | None,
    base_url: str,
) -> ProductRequest:
    cleaned_name = product_name.strip()
    cleaned_message = message.strip()
    if not cleaned_name or not cleaned_message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product name and message cannot be blank")
    if quantity < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantity must be at least 1")

    photo_url, photo_path = await _save_photo(photo, base_url)
    request = ProductRequest(
        buyer_id=buyer.id,
        product_name=cleaned_name,
        quantity=quantity,
        photo_url=photo_url,
        message=cleaned_message,
        status="pending",
    )
    try:
        db.add(request)
        db.commit()
    except Exception:
        db.rollback()
        if photo_path is not None:
            photo_path.unlink(missing_ok=True)
        raise
    db.refresh(request)
    return request


def list_buyer_requests(db: Session, buyer_id: int) -> list[ProductRequest]:
    return list(db.scalars(
        select(ProductRequest)
        .where(ProductRequest.buyer_id == buyer_id)
        .order_by(ProductRequest.created_at.desc(), ProductRequest.id.desc())
    ).all())


def list_admin_requests(db: Session) -> list[ProductRequest]:
    return list(db.scalars(
        select(ProductRequest)
        .options(joinedload(ProductRequest.buyer))
        .order_by(ProductRequest.created_at.desc(), ProductRequest.id.desc())
    ).unique().all())


def respond_to_request(
    db: Session,
    request_id: int,
    response: ProductRequestResponse,
) -> ProductRequest:
    request = db.scalar(
        select(ProductRequest)
        .where(ProductRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product request not found")

    request.status = "responded"
    request.can_arrange = response.can_arrange
    request.price = response.price
    request.expected_delivery_days = response.expected_delivery_days
    request.admin_message = response.admin_message
    request.responded_at = datetime.now(timezone.utc)
    answer = "can be arranged" if response.can_arrange else "cannot be arranged"
    create_notification(
        db,
        user_id=request.buyer_id,
        kind="product_request",
        title="Your product request has a response",
        message=f"The admin {answer} {request.product_name}.",
        link="/requests",
    )
    db.commit()
    updated = db.scalar(
        select(ProductRequest)
        .options(joinedload(ProductRequest.buyer))
        .where(ProductRequest.id == request.id)
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product request not found")
    return updated
