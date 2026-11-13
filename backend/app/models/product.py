from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.shopping_section import ShoppingSection, product_section_assignments

if TYPE_CHECKING:
    from app.models.category import Category


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    offer_discount_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    offer_discount_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    offer_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    stock: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=5, server_default="5", nullable=False)
    low_stock_alert_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    category: Mapped["Category | None"] = relationship(back_populates="products")
    sections: Mapped[list[ShoppingSection]] = relationship(
        secondary=product_section_assignments,
        back_populates="products",
        order_by=ShoppingSection.slug,
    )

    @property
    def offer_active(self) -> bool:
        if not self.offer_is_active or not self.offer_discount_type or self.offer_discount_value is None:
            return False
        now = datetime.now(timezone.utc)
        starts = self.offer_starts_at
        ends = self.offer_ends_at
        if starts and starts.tzinfo is None:
            starts = starts.replace(tzinfo=timezone.utc)
        if ends and ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        return (starts is None or starts <= now) and (ends is None or ends > now)

    @property
    def offer_price(self) -> Decimal | None:
        if not self.offer_active:
            return None
        discount = self.offer_discount_value or Decimal("0")
        amount = self.price * discount / Decimal("100") if self.offer_discount_type == "percentage" else discount
        return max(Decimal("0"), self.price - amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def discount_percentage(self) -> Decimal | None:
        price = self.offer_price
        if price is None or self.price <= 0:
            return None
        return ((self.price - price) * Decimal("100") / self.price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def current_price(self) -> Decimal:
        return self.offer_price if self.offer_price is not None else self.price
