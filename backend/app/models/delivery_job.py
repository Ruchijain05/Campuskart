from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeliveryJob(Base):
    __tablename__ = "delivery_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True)
    delivery_person_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), index=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="assigned", server_default="assigned")
    pickup_location_name: Mapped[str] = mapped_column(String(120), nullable=False)
    failure_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    collected_from_seller_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_by_buyer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    order: Mapped["Order"] = relationship(back_populates="delivery_job")
