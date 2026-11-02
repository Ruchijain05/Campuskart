from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


class SellerEarningsRead(BaseModel):
    total_sales: int
    gross_sales: Decimal
    earnings: Decimal
    eligible_earnings: Decimal
    pending_payments: Decimal
    available_for_payout: Decimal


class PayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    seller_id: int
    amount: Decimal
    status: PayoutStatus
    reference: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None


class SellerPayoutRead(PayoutRead):
    seller_earnings: SellerEarningsRead


class SellerPayoutHistoryRead(BaseModel):
    earnings: SellerEarningsRead
    payouts: list[PayoutRead]


class AdminPayoutRead(PayoutRead):
    seller_name: str
    seller_email: str


class AdminSellerEarningsRead(SellerEarningsRead):
    seller_id: int
    seller_name: str
    seller_email: str


class AdminPayoutDashboardRead(BaseModel):
    sellers: list[AdminSellerEarningsRead]
    payouts: list[AdminPayoutRead]


class PayoutCreate(BaseModel):
    seller_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=2000)


class PayoutUpdate(BaseModel):
    status: PayoutStatus
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=2000)
