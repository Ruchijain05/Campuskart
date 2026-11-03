"""Add email verification and password reset tokens.

Revision ID: 0030_email_actions
Revises: 0029_persistent_sessions
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_email_actions"
down_revision = "0029_persistent_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "email_action_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_email_action_tokens_id", "email_action_tokens", ["id"])
    op.create_index("ix_email_action_tokens_user_id", "email_action_tokens", ["user_id"])
    op.create_index("ix_email_action_tokens_token_hash", "email_action_tokens", ["token_hash"], unique=True)
    op.create_index("ix_email_action_tokens_purpose", "email_action_tokens", ["purpose"])
    op.create_index("ix_email_action_tokens_expires_at", "email_action_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_email_action_tokens_expires_at", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_purpose", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_token_hash", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_user_id", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_id", table_name="email_action_tokens")
    op.drop_table("email_action_tokens")
    op.drop_column("users", "is_email_verified")
