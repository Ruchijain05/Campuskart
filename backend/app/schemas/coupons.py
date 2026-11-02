from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class CouponFields(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    discount_type: Literal["fixed", "percentage"]
    discount_value: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    minimum_order_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    maximum_discount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    usage_limit: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
            raise ValueError("Coupon codes can use letters, numbers, hyphens, and underscores")
        return code

    @model_validator(mode="after")
    def valid_discount_and_dates(self):
        if self.discount_type == "percentage" and self.discount_value > 100:
            raise ValueError("Percentage discount cannot exceed 100")
        if self.starts_at is not None and self.ends_at is not None and _utc(self.starts_at) >= _utc(self.ends_at):
            raise ValueError("Coupon end time must be after its start time")
        return self


class CouponCreate(CouponFields):
    pass


class CouponUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=3, max_length=32)
    discount_type: Literal["fixed", "percentage"] | None = None
    discount_value: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    minimum_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    maximum_discount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    usage_limit: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        code = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
            raise ValueError("Coupon codes can use letters, numbers, hyphens, and underscores")
        return code


class CouponRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: str
    discount_value: Decimal
    minimum_order_amount: Decimal
    maximum_discount: Decimal | None
    usage_limit: int | None
    used_count: int
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime


class CouponValidation(BaseModel):
    code: str = Field(min_length=3, max_length=32)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
            raise ValueError("Enter a valid coupon code")
        return code


class CouponQuote(BaseModel):
    code: str
    discount_type: str
    discount_value: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
