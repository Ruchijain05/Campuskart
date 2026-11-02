from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BuyAgainProductRead(BaseModel):
    product_id: int | None
    product_name: str
    price: Decimal
    image_url: str | None
    stock: int
    available: bool
    unavailable_reason: str | None
    last_ordered_at: datetime
    last_quantity: int
