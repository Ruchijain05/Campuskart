from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


product_section_assignments = Table(
    "product_section_assignments",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("section_slug", ForeignKey("shopping_sections.slug", ondelete="CASCADE"), primary_key=True),
)


class ShoppingSection(Base):
    __tablename__ = "shopping_sections"

    slug: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(
        secondary=product_section_assignments,
        back_populates="sections",
    )
