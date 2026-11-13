"""Create the roles catalog."""

from alembic import op
import sqlalchemy as sa


revision = "0034_roles_catalog"
down_revision = "0033_multi_role_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_name", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_name"),
    )
    roles = sa.table("roles", sa.column("role_name", sa.String(length=32)))
    op.bulk_insert(
        roles,
        [
            {"role_name": "buyer"},
            {"role_name": "seller"},
            {"role_name": "admin"},
            {"role_name": "delivery_person"},
        ],
    )


def downgrade() -> None:
    op.drop_table("roles")