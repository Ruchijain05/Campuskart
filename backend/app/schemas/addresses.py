import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressFields(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=10, max_length=16)
    address_line: str = Field(min_length=5, max_length=1000)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    pin_code: str = Field(min_length=6, max_length=6)

    @field_validator("full_name", "phone_number", "address_line", "city", "state", "pin_code")
    @classmethod
    def strip_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"[+0-9 ()-]{10,16}", value) or sum(char.isdigit() for char in value) < 10:
            raise ValueError("Enter a valid phone number with at least 10 digits")
        return value

    @field_validator("pin_code")
    @classmethod
    def validate_pin_code(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]{6}", value):
            raise ValueError("Enter a valid 6-digit PIN code")
        return value


class AddressCreate(AddressFields):
    is_default: bool = False


class AddressUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone_number: str | None = Field(default=None, min_length=10, max_length=16)
    address_line: str | None = Field(default=None, min_length=5, max_length=1000)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    pin_code: str | None = Field(default=None, min_length=6, max_length=6)
    is_default: bool | None = None

    @field_validator("full_name", "phone_number", "address_line", "city", "state", "pin_code")
    @classmethod
    def strip_optional_values(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None and (not re.fullmatch(r"[+0-9 ()-]{10,16}", value) or sum(char.isdigit() for char in value) < 10):
            raise ValueError("Enter a valid phone number with at least 10 digits")
        return value

    @field_validator("pin_code")
    @classmethod
    def validate_pin_code(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9]{6}", value):
            raise ValueError("Enter a valid 6-digit PIN code")
        return value


class AddressRead(AddressFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
