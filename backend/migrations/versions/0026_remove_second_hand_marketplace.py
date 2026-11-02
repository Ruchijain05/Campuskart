"""Remove second-hand marketplace product fields."""

from alembic import op
import sqlalchemy as sa


revision = "0026_remove_used_market"
down_revision = "0025_buyer_seller_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_columns = {column["name"] for column in inspector.get_columns("products")}

    if "market_type" in product_columns:
        products = sa.table(
            "products",
            sa.column("market_type", sa.String(length=24)),
            sa.column("is_active", sa.Boolean()),
        )
        op.execute(
            products.update()
            .where(products.c.market_type == "second_hand")
            .values(is_active=False)
        )

    product_indexes = {index["name"] for index in inspector.get_indexes("products")}
    if "ix_products_market_type" in product_indexes:
        op.drop_index("ix_products_market_type", table_name="products")
    if "condition" in product_columns:
        op.drop_column("products", "condition")
    if "market_type" in product_columns:
        op.drop_column("products", "market_type")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column("market_type", sa.String(length=24), server_default="regular", nullable=False),
    )
    op.add_column("products", sa.Column("condition", sa.String(length=24), nullable=True))
    op.create_index("ix_products_market_type", "products", ["market_type"])
