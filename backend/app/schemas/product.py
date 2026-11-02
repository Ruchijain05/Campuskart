from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


ShoppingSectionSlug = Literal["male", "female", "special_gifts"]


class ShoppingSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: ShoppingSectionSlug
    name: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0, le=100000)
    image_url: HttpUrl | None = None
    category_id: int | None = Field(default=None, gt=0)
    section_slugs: list[ShoppingSectionSlug] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0, le=100000)
    image_url: HttpUrl | None = None
    category_id: int | None = Field(default=None, gt=0)
    section_slugs: list[ShoppingSectionSlug] | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> "ProductUpdate":
        for field in ("name", "price", "stock", "low_stock_threshold", "section_slugs"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    offer_discount_type: str | None = None
    offer_discount_value: Decimal | None = None
    offer_starts_at: datetime | None = None
    offer_ends_at: datetime | None = None
    offer_is_active: bool = False
    offer_active: bool = False
    offer_price: Decimal | None = None
    discount_percentage: Decimal | None = None
    stock: int
    low_stock_threshold: int
    image_url: str | None
    is_active: bool
    category_id: int | None
    sections: list[ShoppingSectionRead] = Field(default_factory=list)
    seller_id: int | None
    created_at: datetime
    updated_at: datetime


class ProductOfferUpdate(BaseModel):
    discount_type: str = Field(pattern="^(fixed|percentage)$")
    discount_value: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    starts_at: datetime
    ends_at: datetime
    is_active: bool = True

    @model_validator(mode="after")
    def validate_offer(self) -> "ProductOfferUpdate":
        self.starts_at = self.starts_at.replace(tzinfo=timezone.utc) if self.starts_at.tzinfo is None else self.starts_at.astimezone(timezone.utc)
        self.ends_at = self.ends_at.replace(tzinfo=timezone.utc) if self.ends_at.tzinfo is None else self.ends_at.astimezone(timezone.utc)
        if self.ends_at <= self.starts_at:
            raise ValueError("Offer end date must be after its start date")
        if self.discount_type == "percentage" and self.discount_value > 100:
            raise ValueError("Percentage discounts cannot exceed 100")
        return self


class BulkProductRowError(BaseModel):
    row: int
    field: str
    message: str


class BulkProductImportResult(BaseModel):
    imported_count: int
    products: list[ProductRead]
