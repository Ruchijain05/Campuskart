"""Add accounts, sessions, seller review, and product ownership.

Revision ID: 0002_auth
Revises: 0001_catalog
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone_number", sa.String(length=16), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"])
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "seller_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_seller_applications_id", "seller_applications", ["id"])
    op.create_index("ix_seller_applications_user_id", "seller_applications", ["user_id"], unique=True)

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("products", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("seller_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_products_seller_id_users",
                "users",
                ["seller_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_products_seller_id", ["seller_id"])
    else:
        op.add_column("products", sa.Column("seller_id", sa.Integer(), nullable=True))
        op.create_index("ix_products_seller_id", "products", ["seller_id"])
        op.create_foreign_key(
            "fk_products_seller_id_users",
            "products",
            "users",
            ["seller_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("products", recreate="always") as batch_op:
            batch_op.drop_constraint("fk_products_seller_id_users", type_="foreignkey")
            batch_op.drop_index("ix_products_seller_id")
            batch_op.drop_column("seller_id")
    else:
        op.drop_constraint("fk_products_seller_id_users", "products", type_="foreignkey")
        op.drop_index("ix_products_seller_id", table_name="products")
        op.drop_column("products", "seller_id")
    op.drop_index("ix_seller_applications_user_id", table_name="seller_applications")
    op.drop_index("ix_seller_applications_id", table_name="seller_applications")
    op.drop_table("seller_applications")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_family_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
