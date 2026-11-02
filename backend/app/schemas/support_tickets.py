from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketCategory(str, Enum):
    ORDER = "order"
    PRODUCT = "product"
    PAYMENT = "payment"
    ACCOUNT = "account"
    OTHER = "other"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=160)
    category: TicketCategory
    description: str = Field(min_length=1, max_length=5000)

    @field_validator("subject", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class SupportTicketReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reply cannot be blank")
        return value


class SupportTicketStatusUpdate(BaseModel):
    status: TicketStatus


class SupportTicketMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_role: str
    sender_name: str
    body: str
    created_at: datetime


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    category: TicketCategory
    description: str
    status: TicketStatus
    created_at: datetime
    updated_at: datetime


class SupportTicketDetailRead(SupportTicketRead):
    messages: list[SupportTicketMessageRead]


class AdminSupportTicketRead(SupportTicketRead):
    buyer_id: int
    buyer_name: str
    buyer_email: str


class AdminSupportTicketDetailRead(AdminSupportTicketRead):
    messages: list[SupportTicketMessageRead]
