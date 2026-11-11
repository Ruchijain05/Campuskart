"""Add approved CampusKart delivery staff and pickup jobs."""

from alembic import op
import sqlalchemy as sa


revision = "0032_campus_delivery_jobs"
down_revision = "0031_supabase_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("delivery_person_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="assigned", nullable=False),
        sa.Column("pickup_location_name", sa.String(length=120), nullable=False),
        sa.Column("failure_note", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("collected_from_seller_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at_pickup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_by_buyer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_person_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_delivery_jobs_id", "delivery_jobs", ["id"])
    op.create_index("ix_delivery_jobs_order_id", "delivery_jobs", ["order_id"])
    op.create_index("ix_delivery_jobs_delivery_person_id", "delivery_jobs", ["delivery_person_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."delivery_jobs" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_delivery_jobs_delivery_person_id", table_name="delivery_jobs")
    op.drop_index("ix_delivery_jobs_order_id", table_name="delivery_jobs")
    op.drop_index("ix_delivery_jobs_id", table_name="delivery_jobs")
    op.drop_table("delivery_jobs")
