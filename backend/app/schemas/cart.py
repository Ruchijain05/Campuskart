from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)


class CartQuantityUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    stock: int
    image_url: HttpUrl | None
    available: bool
    line_total: Decimal


class CartRead(BaseModel):
    items: list[CartLineRead]
    total: Decimal
