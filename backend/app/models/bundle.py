from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductBundle(Base):
    __tablename__ = "product_bundles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    items: Mapped[list["ProductBundleItem"]] = relationship(back_populates="bundle", cascade="all, delete-orphan", order_by="ProductBundleItem.id")


class ProductBundleItem(Base):
    __tablename__ = "product_bundle_items"
    __table_args__ = (UniqueConstraint("bundle_id", "product_id", name="uq_product_bundle_item"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("product_bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    bundle: Mapped[ProductBundle] = relationship(back_populates="items")
