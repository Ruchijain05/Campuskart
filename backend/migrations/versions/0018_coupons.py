"""Add admin coupons and order discount snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0018_coupons"
down_revision = "0017_razorpay_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_type", sa.String(length=16), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("minimum_order_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("maximum_discount", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_coupons_id", "coupons", ["id"])
    op.create_index("ix_coupons_code", "coupons", ["code"], unique=True)
    op.add_column("orders", sa.Column("coupon_id", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=32), nullable=True))
    op.add_column("orders", sa.Column("subtotal", sa.Numeric(10, 2), nullable=True))
    op.add_column("orders", sa.Column("discount_amount", sa.Numeric(10, 2), server_default="0", nullable=False))
    op.create_index("ix_orders_coupon_id", "orders", ["coupon_id"])
    op.create_foreign_key("fk_orders_coupon_id_coupons", "orders", "coupons", ["coupon_id"], ["id"], ondelete="SET NULL")
    orders = sa.table("orders", sa.column("total", sa.Numeric(10, 2)), sa.column("subtotal", sa.Numeric(10, 2)))
    op.get_bind().execute(orders.update().values(subtotal=orders.c.total))
    op.alter_column("orders", "subtotal", existing_type=sa.Numeric(10, 2), nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_orders_coupon_id_coupons", "orders", type_="foreignkey")
    op.drop_index("ix_orders_coupon_id", table_name="orders")
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "subtotal")
    op.drop_column("orders", "coupon_code")
    op.drop_column("orders", "coupon_id")
    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_index("ix_coupons_id", table_name="coupons")
    op.drop_table("coupons")
