from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConversationStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class StartConversation(BaseModel):
    product_id: int = Field(gt=0)
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class ConversationStatusUpdate(BaseModel):
    status: ConversationStatus


class MessageRead(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    body: str
    is_read: bool
    created_at: datetime


class ConversationRead(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_image_url: str | None
    buyer_id: int
    buyer_name: str
    seller_id: int
    seller_name: str
    other_party_name: str
    status: ConversationStatus
    last_message: str | None
    updated_at: datetime
    unread_count: int


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]
