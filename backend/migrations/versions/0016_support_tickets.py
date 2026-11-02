"""Add buyer support tickets and admin reply messages."""

from alembic import op
import sqlalchemy as sa


revision = "0016_support_tickets"
down_revision = "0015_low_stock_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], name="fk_support_tickets_buyer_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_support_tickets_id", "support_tickets", ["id"])
    op.create_index("ix_support_tickets_buyer_id", "support_tickets", ["buyer_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("sender_role", sa.String(length=16), server_default="admin", nullable=False),
        sa.Column("sender_name", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], name="fk_support_ticket_messages_ticket_id_support_tickets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_support_ticket_messages_sender_id_users", ondelete="SET NULL"),
    )
    op.create_index("ix_support_ticket_messages_id", "support_ticket_messages", ["id"])
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_ticket_messages_sender_id", "support_ticket_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_support_ticket_messages_sender_id", table_name="support_ticket_messages")
    op.drop_index("ix_support_ticket_messages_ticket_id", table_name="support_ticket_messages")
    op.drop_index("ix_support_ticket_messages_id", table_name="support_ticket_messages")
    op.drop_table("support_ticket_messages")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_buyer_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_id", table_name="support_tickets")
    op.drop_table("support_tickets")
