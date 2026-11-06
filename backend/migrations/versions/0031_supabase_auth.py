"""Use Supabase Auth identities and lock app tables behind the API."""

from alembic import op
import sqlalchemy as sa


revision = "0031_supabase_auth"
down_revision = "0030_email_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_user_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_users_auth_user_id", "users", ["auth_user_id"], unique=True)
    op.drop_column("users", "password_hash")
    op.drop_table("email_action_tokens")
    op.drop_table("auth_sessions")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from app import models

        for table_name in models.User.metadata.tables:
            op.execute(
                sa.text(
                    f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY'
                )
            )

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from app import models

        for table_name in models.User.metadata.tables:
            op.execute(
                sa.text(
                    f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY'
                )
            )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"])
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index(
        "ix_auth_sessions_refresh_token_hash",
        "auth_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table(
        "email_action_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_email_action_tokens_id", "email_action_tokens", ["id"])
    op.create_index("ix_email_action_tokens_user_id", "email_action_tokens", ["user_id"])
    op.create_index("ix_email_action_tokens_token_hash", "email_action_tokens", ["token_hash"], unique=True)
    op.create_index("ix_email_action_tokens_purpose", "email_action_tokens", ["purpose"])
    op.create_index("ix_email_action_tokens_expires_at", "email_action_tokens", ["expires_at"])
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.drop_index("ix_users_auth_user_id", table_name="users")
    op.drop_column("users", "auth_user_id")
