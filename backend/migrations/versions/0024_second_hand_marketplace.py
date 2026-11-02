"""Add condition and listing type to products."""

from alembic import op
import sqlalchemy as sa


revision = "0024_second_hand_marketplace"
down_revision = "0023_campus_pickup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("market_type", sa.String(length=24), server_default="regular", nullable=False))
    op.add_column("products", sa.Column("condition", sa.String(length=24), nullable=True))
    op.create_index("ix_products_market_type", "products", ["market_type"])


def downgrade() -> None:
    op.drop_index("ix_products_market_type", table_name="products")
    op.drop_column("products", "condition")
    op.drop_column("products", "market_type")
