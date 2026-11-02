"""Add student product requests."""

from alembic import op
import sqlalchemy as sa


revision = "0028_product_requests"
down_revision = "0027_product_sections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.String(length=2048), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("can_arrange", sa.Boolean(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("expected_delivery_days", sa.Integer(), nullable=True),
        sa.Column("admin_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_requests_id", "product_requests", ["id"])
    op.create_index("ix_product_requests_buyer_id", "product_requests", ["buyer_id"])
    op.create_index("ix_product_requests_status", "product_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_product_requests_status", table_name="product_requests")
    op.drop_index("ix_product_requests_buyer_id", table_name="product_requests")
    op.drop_index("ix_product_requests_id", table_name="product_requests")
    op.drop_table("product_requests")
