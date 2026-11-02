"""Add scheduled product offers without changing product base prices."""

from alembic import op
import sqlalchemy as sa


revision = "0019_product_offers"
down_revision = "0018_coupons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("offer_discount_type", sa.String(length=16), nullable=True))
    op.add_column("products", sa.Column("offer_discount_value", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("offer_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("offer_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("offer_is_active", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column("products", "offer_is_active")
    op.drop_column("products", "offer_ends_at")
    op.drop_column("products", "offer_starts_at")
    op.drop_column("products", "offer_discount_value")
    op.drop_column("products", "offer_discount_type")
