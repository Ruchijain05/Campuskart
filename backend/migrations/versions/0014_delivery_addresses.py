"""Add saved delivery addresses for buyers."""

from alembic import op
import sqlalchemy as sa


revision = "0014_delivery_addresses"
down_revision = "0013_product_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=False),
        sa.Column("address_line", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("pin_code", sa.String(length=6), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_delivery_addresses_user_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_delivery_addresses_id", "delivery_addresses", ["id"])
    op.create_index("ix_delivery_addresses_user_id", "delivery_addresses", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_delivery_addresses_user_id", table_name="delivery_addresses")
    op.drop_index("ix_delivery_addresses_id", table_name="delivery_addresses")
    op.drop_table("delivery_addresses")
