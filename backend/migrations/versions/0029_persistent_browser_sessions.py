"""Add persistent browser-session refresh tokens.

Revision ID: 0029_persistent_sessions
Revises: 0028_product_requests
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_persistent_sessions"
down_revision = "0028_product_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_auth_sessions_refresh_token_hash",
        "auth_sessions",
        ["refresh_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_column("auth_sessions", "refresh_token_hash")
