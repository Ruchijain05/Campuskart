from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _clean_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be blank")
    return value


class ProductQuestionCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return _clean_text(value, "Question")


class ProductAnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=3000)

    @field_validator("answer")
    @classmethod
    def strip_answer(cls, value: str) -> str:
        return _clean_text(value, "Answer")


class ProductQuestionRead(BaseModel):
    id: int
    product_id: int
    product_name: str
    buyer_name: str
    question: str
    answer: str | None
    created_at: datetime
    answered_at: datetime | None
