from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShippingSettingsUpdate(BaseModel):
    delivery_charge: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    estimated_delivery_days: int = Field(ge=1, le=90)


class ShippingSettingsRead(ShippingSettingsUpdate):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime | None = None


class OrderShippingUpdate(BaseModel):
    estimated_delivery_at: datetime | None
    courier_name: str | None = Field(default=None, max_length=120)
    tracking_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def clean_shipping_details(self) -> "OrderShippingUpdate":
        if self.courier_name is not None:
            self.courier_name = self.courier_name.strip() or None
        if self.tracking_id is not None:
            self.tracking_id = self.tracking_id.strip() or None
        return self
