"""Add buyer wishlists.

Revision ID: 0006_wishlist
Revises: 0005_orders
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_wishlist"
down_revision = "0005_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_wishlist_items_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_wishlist_items_product_id_products", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_items_user_product"),
    )
    op.create_index("ix_wishlist_items_id", "wishlist_items", ["id"])
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])
    op.create_index("ix_wishlist_items_product_id", "wishlist_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_wishlist_items_product_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_user_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_id", table_name="wishlist_items")
    op.drop_table("wishlist_items")
