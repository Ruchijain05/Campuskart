from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SellerDashboardOrder(BaseModel):
    id: int
    status: str
    created_at: datetime
    item_count: int
    subtotal: Decimal
    products: list[str]


class SellerDashboardRead(BaseModel):
    total_products: int
    total_orders: int
    total_sales: int
    total_revenue: Decimal
    recent_orders: list[SellerDashboardOrder]
