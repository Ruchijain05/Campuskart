"""Add return requests and refund tracking."""

from alembic import op
import sqlalchemy as sa


revision = "0012_returns_refunds"
down_revision = "0011_product_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "return_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("refund_status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_return_requests_order_id_orders", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], name="fk_return_requests_buyer_id_users", ondelete="CASCADE"),
        sa.UniqueConstraint("order_id", name="uq_return_requests_order_id"),
    )
    op.create_index("ix_return_requests_id", "return_requests", ["id"])
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])
    op.create_index("ix_return_requests_buyer_id", "return_requests", ["buyer_id"])
    op.create_index("ix_return_requests_status", "return_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_return_requests_status", table_name="return_requests")
    op.drop_index("ix_return_requests_buyer_id", table_name="return_requests")
    op.drop_index("ix_return_requests_order_id", table_name="return_requests")
    op.drop_index("ix_return_requests_id", table_name="return_requests")
    op.drop_table("return_requests")
