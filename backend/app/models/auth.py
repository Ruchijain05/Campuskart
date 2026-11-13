from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"
    DELIVERY_PERSON = "delivery_person"


class SellerApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column("user_id", primary_key=True, index=True)
    auth_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), unique=True, index=True, nullable=True)
    full_name: Mapped[str] = mapped_column("name", String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(16))
    role_id: Mapped[int] = mapped_column(ForeignKey("role_master.role_id", ondelete="RESTRICT"), nullable=False)
    active_role: Mapped["Role"] = relationship(foreign_keys=[role_id], lazy="joined")
    role_assignments: Mapped[list["UserRoleMap"]] = relationship(
        foreign_keys="UserRoleMap.user_id", lazy="selectin"
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    @property
    def role(self) -> UserRole:
        return UserRole(self.active_role.role_name)

    @property
    def roles(self) -> list[str]:
        return [assignment.role.role_name for assignment in self.role_assignments]


class SellerApplication(Base):
    __tablename__ = "seller_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SellerApplicationStatus] = mapped_column(
        SqlEnum(
            SellerApplicationStatus,
            native_enum=False,
            values_callable=lambda values: [value.value for value in values],
            length=16,
        ),
        default=SellerApplicationStatus.PENDING,
        nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
