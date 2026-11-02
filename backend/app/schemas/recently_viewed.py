from datetime import datetime

from pydantic import BaseModel

from app.schemas.product import ProductRead


class RecentlyViewedProductRead(BaseModel):
    product: ProductRead
    viewed_at: datetime
