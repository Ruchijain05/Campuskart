"""Rename role tables and move the active role onto users."""

from alembic import op
import sqlalchemy as sa


revision = "0036_role_master_user_role_map"
down_revision = "0035_user_role_assignments"
branch_labels = None
depends_on = None

ROLE_NAMES = {"buyer", "seller", "admin", "delivery_person"}


def _role_backfill(bind):
    roles = sa.table(
        "roles", sa.column("role_id", sa.Integer()), sa.column("role_name", sa.String())
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("role", sa.String()),
        sa.column("roles", sa.JSON()),
    )
    assignments = sa.table(
        "user_role_assignments",
        sa.column("user_id", sa.Integer()),
        sa.column("role_id", sa.Integer()),
        sa.column("status", sa.String()),
    )
    role_ids = {
        row.role_name: row.role_id
        for row in bind.execute(sa.select(roles.c.role_id, roles.c.role_name))
    }
    missing_roles = sorted(ROLE_NAMES - role_ids.keys())
    if missing_roles:
        raise RuntimeError("0036 requires role catalog entries: " + ", ".join(missing_roles))

    inactive = list(
        bind.execute(
            sa.select(assignments.c.user_id, assignments.c.role_id)
            .where(assignments.c.status != "active")
        )
    )
    if inactive:
        raise RuntimeError(
            f"0036 found {len(inactive)} inactive role mappings. The target map has no status column; "
            "migration stopped before schema changes so revoked roles are not granted or discarded."
        )

    existing = {
        (row.user_id, row.role_id)
        for row in bind.execute(sa.select(assignments.c.user_id, assignments.c.role_id))
    }
    active_roles: dict[int, int] = {}
    required = set(existing)
    errors = []
    for row in bind.execute(sa.select(users.c.id, users.c.role, users.c.roles)):
        if not isinstance(row.roles, list):
            errors.append(f"user_id={row.id}: roles must be a JSON list, got {row.roles!r}")
            names = set()
        else:
            names = set()
            for value in row.roles:
                if not isinstance(value, str) or value not in ROLE_NAMES:
                    errors.append(f"user_id={row.id}: invalid assigned role {value!r}")
                else:
                    names.add(value)

        if not isinstance(row.role, str) or row.role not in role_ids:
            errors.append(f"user_id={row.id}: invalid active role {row.role!r}")
            continue
        active_role_id = role_ids[row.role]
        active_roles[row.id] = active_role_id
        names.add(row.role)
        required.update((row.id, role_ids[name]) for name in names)

    if errors:
        raise RuntimeError("0036 role backfill validation failed:\n" + "\n".join(errors[:50]))
    return active_roles, sorted(required - existing)


def upgrade() -> None:
    bind = op.get_bind()
    active_roles, missing_assignments = _role_backfill(bind)

    if bind.dialect.name == "postgresql":
        # These triggers refer to the legacy status and history columns.
        op.execute("DROP TRIGGER IF EXISTS campus_kart_0035_buyer_assignment_guard ON public.user_role_assignments")
        op.execute("DROP FUNCTION IF EXISTS public.campus_kart_0035_prevent_buyer_deactivation()")
        op.execute("DROP TRIGGER IF EXISTS campus_kart_0035_history_no_update_delete ON public.user_role_assignment_history")
        op.execute("DROP TRIGGER IF EXISTS campus_kart_0035_history_no_truncate ON public.user_role_assignment_history")
        op.execute("DROP FUNCTION IF EXISTS public.campus_kart_0035_reject_history_mutation()")

    # Keep the existing role and assignment primary keys and all references.
    op.rename_table("roles", "role_master")
    op.rename_table("user_role_assignments", "user_role_map")
    op.alter_column("user_role_map", "assignment_id", new_column_name="id")

    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    users = sa.table("users", sa.column("id", sa.Integer()), sa.column("role_id", sa.Integer()))
    for user_id, role_id in active_roles.items():
        bind.execute(users.update().where(users.c.id == user_id).values(role_id=role_id))

    op.alter_column("users", "role_id", nullable=False)
    op.create_foreign_key(
        "fk_users_role_id_role_master", "users", "role_master", ["role_id"], ["role_id"], ondelete="RESTRICT"
    )

    # Backfill every role from users.roles, plus all existing 0035 mappings.
    user_role_map = sa.table(
        "user_role_map",
        sa.column("user_id", sa.Integer()),
        sa.column("role_id", sa.Integer()),
    )
    if missing_assignments:
        bind.execute(
            sa.insert(user_role_map),
            [{"user_id": user_id, "role_id": role_id} for user_id, role_id in missing_assignments],
        )

    op.drop_column("user_role_map", "status")
    op.drop_column("users", "roles")
    op.drop_column("users", "role")

    # Keep every existing ID and let the database update dependent foreign keys.
    op.alter_column("users", "id", new_column_name="user_id")
    op.alter_column("users", "full_name", new_column_name="name")

    # Remove the obsolete history table and its index after renaming its parent.
    op.drop_index(
        "ix_user_role_assignment_history_assignment_id",
        table_name="user_role_assignment_history",
    )
    op.drop_table("user_role_assignment_history")

def downgrade() -> None:
    raise RuntimeError("Migration 0036 is intentionally irreversible after legacy role data is removed.")
