from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PickupLocationInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address_line: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=4, max_length=20)
    instructions: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("name", "address_line", "city", "state", "postal_code")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("instructions")
    @classmethod
    def clean_instructions(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class PickupLocationRead(PickupLocationInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
