from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class OrderStatus(str, Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderCreate(BaseModel):
    delivery_name: str = Field(min_length=1, max_length=120)
    delivery_phone: str = Field(min_length=10, max_length=16)
    address_line: str = Field(min_length=5, max_length=1000)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=4, max_length=20)
    coupon_code: str | None = Field(default=None, min_length=3, max_length=32)
    delivery_method: str = Field(default="home_delivery", pattern="^(home_delivery|campus_pickup)$")
    pickup_location_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_fulfillment(self) -> "OrderCreate":
        if self.delivery_method == "campus_pickup" and self.pickup_location_id is None:
            raise ValueError("Choose a campus pickup location")
        if self.delivery_method == "home_delivery" and self.pickup_location_id is not None:
            raise ValueError("Pickup location can only be used for campus pickup")
        return self

    @field_validator("delivery_name", "delivery_phone", "address_line", "city", "state", "postal_code")
    @classmethod
    def strip_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("delivery_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"[+0-9 ()-]{10,16}", value) or sum(char.isdigit() for char in value) < 10:
            raise ValueError("Enter a valid phone number with at least 10 digits")
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9 -]{4,20}", value):
            raise ValueError("Enter a valid postal code")
        return value

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", value):
            raise ValueError("Coupon codes can use letters, numbers, hyphens, and underscores")
        return value


class RazorpayPaymentStart(OrderCreate):
    pass

class RazorpayPaymentStartRead(BaseModel):
    key_id: str
    razorpay_order_id: str
    amount: int
    currency: str
    order: "OrderRead"


class RazorpayPaymentVerification(BaseModel):
    razorpay_order_id: str = Field(min_length=1, max_length=64)
    razorpay_payment_id: str = Field(min_length=1, max_length=64)
    razorpay_signature: str = Field(min_length=1, max_length=128)

class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    payment_method: str
    payment_status: str
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    coupon_code: str | None = None
    discount_description: str | None = None
    delivery_method: str = "home_delivery"
    pickup_location_id: int | None = None
    pickup_location_name: str | None = None
    pickup_status: str = "not_applicable"
    delivery_name: str
    delivery_phone: str
    address_line: str
    city: str
    state: str
    postal_code: str
    subtotal: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal = Decimal("0.00")
    estimated_delivery_at: datetime | None = None
    courier_name: str | None = None
    tracking_id: str | None = None
    total: Decimal
    created_at: datetime
    items: list[OrderItemRead]

    @field_serializer("estimated_delivery_at")
    def serialize_estimated_delivery_at(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class FulfillmentStatus(str, Enum):
    PROCESSING = "processing"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class FulfillmentStatusUpdate(BaseModel):
    status: FulfillmentStatus


class SellerOrderItemRead(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    fulfillment_status: FulfillmentStatus


class SellerOrderRead(BaseModel):
    id: int
    status: OrderStatus
    payment_method: str
    payment_status: str
    delivery_name: str
    delivery_phone: str
    address_line: str
    city: str
    state: str
    postal_code: str
    seller_subtotal: Decimal
    created_at: datetime
    items: list[SellerOrderItemRead]
