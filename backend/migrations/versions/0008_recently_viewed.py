"""Add buyer-specific recently viewed products."""

from alembic import op
import sqlalchemy as sa


revision = "0008_recently_viewed"
down_revision = "0007_product_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recently_viewed_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_recently_viewed_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_recently_viewed_product_id_products", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_recently_viewed_user_product"),
    )
    op.create_index("ix_recently_viewed_products_id", "recently_viewed_products", ["id"])
    op.create_index("ix_recently_viewed_products_user_id", "recently_viewed_products", ["user_id"])
    op.create_index("ix_recently_viewed_products_product_id", "recently_viewed_products", ["product_id"])
    op.create_index("ix_recently_viewed_products_viewed_at", "recently_viewed_products", ["viewed_at"])


def downgrade() -> None:
    op.drop_index("ix_recently_viewed_products_viewed_at", table_name="recently_viewed_products")
    op.drop_index("ix_recently_viewed_products_product_id", table_name="recently_viewed_products")
    op.drop_index("ix_recently_viewed_products_user_id", table_name="recently_viewed_products")
    op.drop_index("ix_recently_viewed_products_id", table_name="recently_viewed_products")
    op.drop_table("recently_viewed_products")
