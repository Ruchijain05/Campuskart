"""Add campus pickup locations and order fulfillment snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0023_campus_pickup"
down_revision = "0022_product_bundles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campus_pickup_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address_line", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campus_pickup_locations_id", "campus_pickup_locations", ["id"])
    op.create_index("ix_campus_pickup_locations_is_active", "campus_pickup_locations", ["is_active"])
    op.add_column("orders", sa.Column("delivery_method", sa.String(length=24), server_default="home_delivery", nullable=False))
    op.add_column("orders", sa.Column("pickup_location_id", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("pickup_location_name", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("pickup_status", sa.String(length=24), server_default="not_applicable", nullable=False))
    op.create_index("ix_orders_pickup_location_id", "orders", ["pickup_location_id"])
    op.create_foreign_key(
        "fk_orders_pickup_location_id_campus_pickup_locations",
        "orders", "campus_pickup_locations", ["pickup_location_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_pickup_location_id_campus_pickup_locations", "orders", type_="foreignkey")
    op.drop_index("ix_orders_pickup_location_id", table_name="orders")
    op.drop_column("orders", "pickup_status")
    op.drop_column("orders", "pickup_location_name")
    op.drop_column("orders", "pickup_location_id")
    op.drop_column("orders", "delivery_method")
    op.drop_index("ix_campus_pickup_locations_is_active", table_name="campus_pickup_locations")
    op.drop_index("ix_campus_pickup_locations_id", table_name="campus_pickup_locations")
    op.drop_table("campus_pickup_locations")
