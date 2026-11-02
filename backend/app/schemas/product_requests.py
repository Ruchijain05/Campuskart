from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductRequestResponse(BaseModel):
    can_arrange: bool
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    expected_delivery_days: int | None = Field(default=None, ge=1, le=365)
    admin_message: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_response_details(self) -> "ProductRequestResponse":
        self.admin_message = self.admin_message.strip()
        if not self.admin_message:
            raise ValueError("Response message cannot be blank")
        if self.can_arrange and (self.price is None or self.expected_delivery_days is None):
            raise ValueError("Price and expected delivery time are required when the product can be arranged")
        if not self.can_arrange and (self.price is not None or self.expected_delivery_days is not None):
            raise ValueError("Price and expected delivery time must be omitted when the product cannot be arranged")
        return self


class ProductRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    quantity: int
    photo_url: str | None
    message: str
    status: str
    can_arrange: bool | None
    price: Decimal | None
    expected_delivery_days: int | None
    admin_message: str | None
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None


class AdminProductRequestRead(ProductRequestRead):
    buyer_id: int
    buyer_name: str
    buyer_email: str
