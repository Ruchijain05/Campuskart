from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShippingSettings(Base):
    __tablename__ = "shipping_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    estimated_delivery_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
