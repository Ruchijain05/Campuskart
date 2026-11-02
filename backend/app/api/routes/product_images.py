from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.product_image import ProductImageRead
from app.services import product_images as image_service

router = APIRouter(tags=["product images"])


async def _read_files(files: list[UploadFile]) -> list[bytes]:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose at least one image")
    if len(files) > image_service.MAX_PRODUCT_IMAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Upload at most {image_service.MAX_PRODUCT_IMAGES} images at a time")
    contents: list[bytes] = []
    total_size = 0
    try:
        for upload in files:
            data = await upload.read(image_service.MAX_IMAGE_BYTES + 1)
            if len(data) > image_service.MAX_IMAGE_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Each image must be 5 MB or smaller")
            total_size += len(data)
            if total_size > 20 * 1024 * 1024:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The total image upload must be 20 MB or smaller")
            contents.append(data)
    finally:
        for upload in files:
            await upload.close()
    return contents


@router.get("/products/{product_id}/images", response_model=list[ProductImageRead])
def list_product_images(product_id: int, db: Session = Depends(get_db)) -> list[ProductImageRead]:
    return image_service.list_product_images(db, product_id)


@router.post("/products/{product_id}/images", response_model=list[ProductImageRead], status_code=status.HTTP_201_CREATED)
async def upload_product_images(
    product_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[ProductImageRead]:
    contents = await _read_files(files)
    return image_service.upload_product_images(
        db,
        product_id=product_id,
        seller_id=seller.id,
        uploads=contents,
        base_url=str(request.base_url),
    )


@router.patch("/products/{product_id}/images/{image_id}/primary", response_model=list[ProductImageRead])
def select_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[ProductImageRead]:
    return image_service.set_primary_image(db, product_id=product_id, seller_id=seller.id, image_id=image_id)


@router.put("/products/{product_id}/images/{image_id}", response_model=list[ProductImageRead])
async def replace_product_image(
    product_id: int,
    image_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[ProductImageRead]:
    contents = await _read_files([file])
    return image_service.replace_product_image(
        db,
        product_id=product_id,
        seller_id=seller.id,
        image_id=image_id,
        data=contents[0],
        base_url=str(request.base_url),
    )


@router.delete("/products/{product_id}/images/{image_id}", response_model=list[ProductImageRead])
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.SELLER)),
) -> list[ProductImageRead]:
    return image_service.delete_product_image(db, product_id=product_id, seller_id=seller.id, image_id=image_id)
