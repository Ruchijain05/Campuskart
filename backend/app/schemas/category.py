from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None, gt=0)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name_not_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Name cannot be null")
        return value


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    parent_id: int | None


class CategoryTreeRead(CategoryRead):
    children: list["CategoryTreeRead"] = Field(default_factory=list)
