"""Track fulfillment per order item for sellers."""

from alembic import op
import sqlalchemy as sa


revision = "0010_seller_fulfillment"
down_revision = "0009_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("fulfillment_status", sa.String(length=24), server_default="processing", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("order_items", "fulfillment_status")
