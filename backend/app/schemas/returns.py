from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ReturnType(str, Enum):
    RETURN = "return"
    REFUND = "refund"


class ReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefundStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REFUNDED = "refunded"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class ReturnRequestCreate(BaseModel):
    request_type: ReturnType
    reason: str = Field(min_length=1, max_length=3000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please provide a reason")
        return value


class ReturnDecisionUpdate(BaseModel):
    decision: ReturnStatus
    review_note: str | None = Field(default=None, max_length=1000)

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value: ReturnStatus) -> ReturnStatus:
        if value == ReturnStatus.PENDING:
            raise ValueError("Decision must be approved or rejected")
        return value

    @field_validator("review_note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class RefundStatusUpdate(BaseModel):
    status: RefundStatus


class ReturnRequestRead(BaseModel):
    id: int
    order_id: int
    request_type: ReturnType
    reason: str
    status: ReturnStatus
    refund_status: RefundStatus
    review_note: str | None
    order_status: str
    order_total: Decimal
    payment_method: str
    created_at: datetime
    reviewed_at: datetime | None
    refund_updated_at: datetime | None


class AdminReturnRequestRead(ReturnRequestRead):
    buyer_id: int
    buyer_name: str
    buyer_email: str
