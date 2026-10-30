import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.auth import SellerApplicationStatus, UserRole


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: str = Field(min_length=10, max_length=10, pattern=r"^[0-9]{10}$")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must include at least one letter, one number, and one special character")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must include at least one letter, one number, and one special character")
        if not re.search(r"[^A-Za-z0-9\s]", value):
            raise ValueError("Password must include at least one letter, one number, and one special character")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned

    @field_validator("phone_number", mode="before")
    @classmethod
    def strip_phone_whitespace(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class OAuth2Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    role: UserRole
    created_at: datetime


class SellerApplicationCreate(BaseModel):
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SellerApplicationDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class SellerApplicationReview(BaseModel):
    decision: SellerApplicationDecision
    review_note: str | None = Field(default=None, max_length=500)

    @field_validator("review_note")
    @classmethod
    def strip_review_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SellerApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    message: str | None
    status: SellerApplicationStatus
    reviewed_by: int | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
