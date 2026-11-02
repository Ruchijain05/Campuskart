"""Add product low-stock thresholds and duplicate alert state."""

from alembic import op
import sqlalchemy as sa


revision = "0015_low_stock_alerts"
down_revision = "0014_delivery_addresses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("low_stock_threshold", sa.Integer(), server_default="5", nullable=False))
    op.add_column("products", sa.Column("low_stock_alert_active", sa.Boolean(), server_default=sa.false(), nullable=False))

    connection = op.get_bind()
    products = sa.table(
        "products",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=150)),
        sa.column("stock", sa.Integer()),
        sa.column("seller_id", sa.Integer()),
        sa.column("low_stock_threshold", sa.Integer()),
        sa.column("low_stock_alert_active", sa.Boolean()),
    )
    notifications = sa.table(
        "notifications",
        sa.column("user_id", sa.Integer()),
        sa.column("kind", sa.String(length=40)),
        sa.column("title", sa.String(length=160)),
        sa.column("message", sa.Text()),
        sa.column("link", sa.String(length=255)),
        sa.column("is_read", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    low_products = connection.execute(
        sa.select(
            products.c.id,
            products.c.name,
            products.c.stock,
            products.c.seller_id,
            products.c.low_stock_threshold,
        ).where(
            products.c.seller_id.is_not(None),
            products.c.stock <= products.c.low_stock_threshold,
        )
    ).all()
    for product_id, name, stock, seller_id, threshold in low_products:
        connection.execute(notifications.insert().values(
            user_id=seller_id,
            kind="low_stock",
            title="Low stock alert",
            message=f"{name} has {stock} left (low-stock threshold: {threshold}).",
            link="/seller/products",
            is_read=False,
            created_at=sa.func.now(),
        ))
        connection.execute(products.update().where(products.c.id == product_id).values(low_stock_alert_active=True))


def downgrade() -> None:
    op.drop_column("products", "low_stock_alert_active")
    op.drop_column("products", "low_stock_threshold")
