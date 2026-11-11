"""Store assigned roles separately from the active role."""

from alembic import op
import sqlalchemy as sa


revision = "0033_multi_role_accounts"
down_revision = "0032_campus_delivery_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("roles", sa.JSON(), nullable=True))
    bind = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("role", sa.String))
    roles = sa.table("users", sa.column("id", sa.Integer), sa.column("roles", sa.JSON))
    for row in bind.execute(sa.select(users.c.id, users.c.role)):
        bind.execute(roles.update().where(roles.c.id == row.id).values(roles=[row.role]))
    op.alter_column("users", "roles", nullable=False, server_default="[]")


def downgrade() -> None:
    op.drop_column("users", "roles")
