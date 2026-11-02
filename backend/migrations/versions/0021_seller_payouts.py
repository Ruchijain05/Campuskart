"""Add seller payout records."""

from alembic import op
import sqlalchemy as sa


revision = "0021_seller_payouts"
down_revision = "0020_shipping_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("seller_id", sa.Integer(), nullable=True))
    op.create_index("ix_order_items_seller_id", "order_items", ["seller_id"])
    op.create_foreign_key("fk_order_items_seller_id_users", "order_items", "users", ["seller_id"], ["id"], ondelete="SET NULL")
    op.execute(sa.text(
        "UPDATE order_items SET seller_id = "
        "(SELECT products.seller_id FROM products WHERE products.id = order_items.product_id) "
        "WHERE seller_id IS NULL AND product_id IS NOT NULL"
    ))
    op.create_table(
        "seller_payouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_seller_payouts_id", "seller_payouts", ["id"])
    op.create_index("ix_seller_payouts_seller_id", "seller_payouts", ["seller_id"])
    op.create_index("ix_seller_payouts_status", "seller_payouts", ["status"])


def downgrade() -> None:
    op.drop_constraint("fk_order_items_seller_id_users", "order_items", type_="foreignkey")
    op.drop_index("ix_order_items_seller_id", table_name="order_items")
    op.drop_column("order_items", "seller_id")
    op.drop_index("ix_seller_payouts_status", table_name="seller_payouts")
    op.drop_index("ix_seller_payouts_seller_id", table_name="seller_payouts")
    op.drop_index("ix_seller_payouts_id", table_name="seller_payouts")
    op.drop_table("seller_payouts")
