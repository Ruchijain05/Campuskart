"""Add product bundles and bundle discount snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0022_product_bundles"
down_revision = "0021_seller_payouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("discount_description", sa.String(length=80), nullable=True))
    op.create_table(
        "product_bundles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("special_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_product_bundles_id", "product_bundles", ["id"])
    op.create_index("ix_product_bundles_is_active", "product_bundles", ["is_active"])
    op.create_table(
        "product_bundle_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bundle_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["product_bundles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("bundle_id", "product_id", name="uq_product_bundle_item"),
    )
    op.create_index("ix_product_bundle_items_id", "product_bundle_items", ["id"])
    op.create_index("ix_product_bundle_items_bundle_id", "product_bundle_items", ["bundle_id"])
    op.create_index("ix_product_bundle_items_product_id", "product_bundle_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_bundle_items_product_id", table_name="product_bundle_items")
    op.drop_index("ix_product_bundle_items_bundle_id", table_name="product_bundle_items")
    op.drop_index("ix_product_bundle_items_id", table_name="product_bundle_items")
    op.drop_table("product_bundle_items")
    op.drop_index("ix_product_bundles_is_active", table_name="product_bundles")
    op.drop_index("ix_product_bundles_id", table_name="product_bundles")
    op.drop_table("product_bundles")
    op.drop_column("orders", "discount_description")
