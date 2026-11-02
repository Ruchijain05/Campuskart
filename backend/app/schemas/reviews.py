from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=1, max_length=3000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Review text cannot be blank")
        return value


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    body: str | None = Field(default=None, min_length=1, max_length=3000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Review text cannot be blank")
        return value

    @model_validator(mode="after")
    def require_an_update(self) -> "ReviewUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide a rating or review text to update")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    reviewer_name: str
    rating: int
    body: str
    created_at: datetime
    updated_at: datetime


class ReviewSummary(BaseModel):
    average_rating: Decimal | None
    review_count: int
    reviews: list[ReviewRead]
