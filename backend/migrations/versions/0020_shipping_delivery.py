"""Add delivery charges and order tracking details."""

from alembic import op
import sqlalchemy as sa


revision = "0020_shipping_delivery"
down_revision = "0019_product_offers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("shipping_fee", sa.Numeric(10, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("estimated_delivery_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("courier_name", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("tracking_id", sa.String(length=120), nullable=True))
    op.create_table(
        "shipping_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("delivery_charge", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("estimated_delivery_days", sa.Integer(), server_default="5", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("shipping_settings")
    op.drop_column("orders", "tracking_id")
    op.drop_column("orders", "courier_name")
    op.drop_column("orders", "estimated_delivery_at")
    op.drop_column("orders", "shipping_fee")
