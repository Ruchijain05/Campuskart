from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.orders import OrderCreate


class BundleComponentInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)


class BundleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=4000)
    special_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    items: list[BundleComponentInput] = Field(min_length=2, max_length=20)
    is_active: bool = True

    @model_validator(mode="after")
    def unique_components(self) -> "BundleCreate":
        ids = [item.product_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each product can appear only once in a bundle")
        return self


class BundleUpdate(BundleCreate):
    pass


class BundleComponentRead(BaseModel):
    product_id: int
    product_name: str
    image_url: str | None
    quantity: int
    unit_price: Decimal
    available_stock: int


class BundleRead(BaseModel):
    id: int
    name: str
    description: str | None
    special_price: Decimal
    payable_price: Decimal
    original_price: Decimal
    discount_amount: Decimal
    discount_percentage: Decimal
    is_active: bool
    available: bool
    max_bundles: int
    created_at: datetime
    updated_at: datetime
    items: list[BundleComponentRead]


class BundleOrderCreate(OrderCreate):
    quantity: int = Field(default=1, ge=1, le=20)
