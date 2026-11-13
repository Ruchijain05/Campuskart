from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="placed")
    payment_method: Mapped[str] = mapped_column(String(24), nullable=False, default="cod")
    payment_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True, index=True)
    coupon_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    discount_description: Mapped[str | None] = mapped_column(String(80), nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(24), nullable=False, default="home_delivery", server_default="home_delivery")
    pickup_location_id: Mapped[int | None] = mapped_column(ForeignKey("campus_pickup_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    pickup_location_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pickup_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_applicable", server_default="not_applicable")
    delivery_name: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    courier_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tracking_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id")
    delivery_job: Mapped["DeliveryJob | None"] = relationship(back_populates="order", uselist=False)

    @property
    def delivery_job_status(self) -> str | None:
        return self.delivery_job.status if self.delivery_job is not None else None


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(String(24), nullable=False, default="processing", server_default="processing")

    order: Mapped[Order] = relationship(back_populates="items")
