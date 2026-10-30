from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    image_url: HttpUrl | None = None
    category_id: int | None = Field(default=None, gt=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    image_url: HttpUrl | None = None
    category_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "ProductUpdate":
        for field in ("name", "price", "stock"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    stock: int
    image_url: str | None
    is_active: bool
    category_id: int | None
    created_at: datetime
    updated_at: datetime


class BulkProductRowError(BaseModel):
    row: int
    field: str
    message: str


class BulkProductImportResult(BaseModel):
    imported_count: int
    products: list[ProductRead]
