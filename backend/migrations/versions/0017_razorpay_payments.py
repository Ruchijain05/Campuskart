"""Store Razorpay order and payment references on orders."""

from alembic import op
import sqlalchemy as sa


revision = "0017_razorpay_payments"
down_revision = "0016_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("razorpay_order_id", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("razorpay_payment_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_orders_razorpay_order_id", "orders", ["razorpay_order_id"])
    op.create_unique_constraint("uq_orders_razorpay_payment_id", "orders", ["razorpay_payment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_orders_razorpay_payment_id", "orders", type_="unique")
    op.drop_constraint("uq_orders_razorpay_order_id", "orders", type_="unique")
    op.drop_column("orders", "razorpay_payment_id")
    op.drop_column("orders", "razorpay_order_id")
