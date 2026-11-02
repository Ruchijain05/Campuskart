from pydantic import BaseModel


class LowStockProductRead(BaseModel):
    id: int
    name: str
    stock: int
    low_stock_threshold: int
    seller_id: int | None
    seller_name: str | None
    image_url: str | None
