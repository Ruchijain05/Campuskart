from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AdminDailySummary(BaseModel):
    date: str
    orders: int
    registrations: int


class AdminActivity(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    created_at: datetime


class AdminDashboardRead(BaseModel):
    total_users: int
    buyers: int
    sellers: int
    delivery_persons: int = 0
    total_products: int
    total_orders: int
    total_revenue: Decimal
    daily_summary: list[AdminDailySummary]
    recent_activities: list[AdminActivity]
