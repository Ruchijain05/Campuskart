from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DeliveryPersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone_number: str


class DeliveryPersonCreate(BaseModel):
    email: EmailStr


class DeliveryJobAssign(BaseModel):
    delivery_person_id: int = Field(gt=0)


class DeliveryJobStatusUpdate(BaseModel):
    status: str = Field(pattern="^(collected_from_seller|ready_at_pickup|collected_by_buyer|delivery_issue)$")
    failure_note: str | None = Field(default=None, max_length=1000)


class DeliverySellerContact(BaseModel):
    full_name: str
    phone_number: str
    products: list[str]


class DeliveryJobRead(BaseModel):
    id: int
    order_id: int
    delivery_person_id: int
    status: str
    pickup_location_name: str
    buyer_name: str
    buyer_phone: str
    pickup_address: str
    sellers: list[DeliverySellerContact]
    products: list[str]
    failure_note: str | None
    assigned_at: datetime
    collected_from_seller_at: datetime | None
    ready_at_pickup_at: datetime | None
    collected_by_buyer_at: datetime | None
    updated_at: datetime
