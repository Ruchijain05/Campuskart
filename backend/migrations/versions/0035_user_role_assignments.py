"""Create normalized user-role assignments and append-only history."""

from alembic import op
import sqlalchemy as sa

from app.core.config import settings


revision = "0035_user_role_assignments"
down_revision = "0034_roles_catalog"
branch_labels = None
depends_on = None


ROLE_NAMES = {"buyer", "seller", "admin", "delivery_person"}
ROLES_POLICY = "campuskart_0035_roles_read"
ASSIGNMENTS_SELECT_POLICY = "campuskart_0035_assignments_select"
ASSIGNMENTS_INSERT_POLICY = "campuskart_0035_assignments_insert"
ASSIGNMENTS_UPDATE_POLICY = "campuskart_0035_assignments_update"
HISTORY_SELECT_POLICY = "campuskart_0035_history_select"
HISTORY_INSERT_POLICY = "campuskart_0035_history_insert"


def _application_role_name() -> str:
    """Return the explicitly configured PostgreSQL role for the backend."""
    role_name = settings.app_database_role.strip()
    if not role_name:
        raise RuntimeError(
            "Migration 0035 requires APP_DATABASE_ROLE so it can grant "
            "privileges to the backend role."
        )
    if role_name.lower() in {"anon", "authenticated", "service_role"}:
        raise RuntimeError(
            "APP_DATABASE_ROLE must be a dedicated backend database role, not "
            "anon, authenticated, or service_role."
        )
    return role_name


def _quoted_role(bind, role_name: str) -> str:
    return bind.dialect.identifier_preparer.quote(role_name)


def _ensure_runtime_role_is_restricted(bind, role_name: str) -> None:
    """Require a separate login role that cannot bypass row-level security."""
    if bind.dialect.name != "postgresql":
        return
    migration_role = bind.execute(sa.text("SELECT current_user")).scalar_one()
    if role_name == migration_role:
        raise RuntimeError(
            "APP_DATABASE_ROLE must differ from the migration connection role."
        )
    role = bind.execute(
        sa.text(
            "SELECT rolcanlogin, rolsuper, rolbypassrls, "
            "rolcreaterole, rolcreatedb, rolreplication "
            "FROM pg_roles WHERE rolname = :role_name"
        ),
        {"role_name": role_name},
    ).one_or_none()
    if role is None:
        raise RuntimeError(f"APP_DATABASE_ROLE {role_name!r} does not exist in PostgreSQL.")

    has_role_membership = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM pg_roles AS candidate_role "
            "WHERE candidate_role.rolname <> :role_name "
            "AND pg_has_role(:role_name, candidate_role.rolname, 'MEMBER')"
            ")"
        ),
        {"role_name": role_name},
    ).scalar_one()

    unsafe_attributes = []
    if role.rolsuper:
        unsafe_attributes.append("SUPERUSER")
    if role.rolbypassrls:
        unsafe_attributes.append("BYPASSRLS")
    if role.rolcreaterole:
        unsafe_attributes.append("CREATEROLE")
    if role.rolcreatedb:
        unsafe_attributes.append("CREATEDB")
    if role.rolreplication:
        unsafe_attributes.append("REPLICATION")
    if has_role_membership:
        unsafe_attributes.append("membership in another PostgreSQL role")

    if not role.rolcanlogin:
        raise RuntimeError(
            "APP_DATABASE_ROLE must have LOGIN enabled."
        )
    if unsafe_attributes:
        raise RuntimeError(
            "APP_DATABASE_ROLE has unsafe PostgreSQL privileges: "
            + ", ".join(unsafe_attributes)
            + ". Disable these attributes and remove its role memberships before migration."
        )


def _ensure_roles_table_owner(bind) -> None:
    """RLS on roles can only be changed by its owner or a PostgreSQL superuser."""
    if bind.dialect.name != "postgresql":
        return
    owner = bind.execute(
        sa.text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = to_regclass('public.roles')")
    ).scalar_one_or_none()
    is_superuser = bind.execute(
        sa.text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    ).scalar_one_or_none()
    if owner is None:
        raise RuntimeError("Migration 0035 requires public.roles from migration 0034.")
    if owner != bind.execute(sa.text("SELECT current_user")).scalar_one() and not is_superuser:
        raise RuntimeError(
            "The migration execution role must own public.roles or be a PostgreSQL superuser. "
            "The configured APP_DATABASE_ROLE is granted separately."
        )


def _validated_backfill(bind):
    roles = sa.table(
        "roles",
        sa.column("role_id", sa.Integer),
        sa.column("role_name", sa.String),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("role", sa.String),
        sa.column("roles", sa.JSON),
    )

    role_ids = {
        row.role_name: row.role_id
        for row in bind.execute(sa.select(roles.c.role_id, roles.c.role_name))
    }
    missing_catalog_roles = sorted(ROLE_NAMES - role_ids.keys())
    if missing_catalog_roles:
        raise RuntimeError(
            "Migration 0035 requires all four role rows in roles; missing: "
            + ", ".join(missing_catalog_roles)
        )

    assignments = []
    errors = []
    for row in bind.execute(sa.select(users.c.id, users.c.role, users.c.roles)):
        if not isinstance(row.roles, list):
            errors.append(f"user_id={row.id}: roles must be a JSON list, got {row.roles!r}")
            role_values = []
        else:
            role_values = row.roles

        assigned_names = set()
        for value in role_values:
            if not isinstance(value, str) or value not in ROLE_NAMES:
                errors.append(f"user_id={row.id}: invalid assigned role {value!r}")
            else:
                assigned_names.add(value)

        if not isinstance(row.role, str) or row.role not in ROLE_NAMES:
            errors.append(f"user_id={row.id}: invalid active role {row.role!r}")
        else:
            # Active role must be an assignment even if an older roles list omitted it.
            assigned_names.add(row.role)

        if assigned_names and all(name in role_ids for name in assigned_names):
            assignments.extend((row.id, name, role_ids[name]) for name in sorted(assigned_names))

    if errors:
        details = "\n".join(errors[:50])
        suffix = f"\n... and {len(errors) - 50} more invalid values" if len(errors) > 50 else ""
        raise RuntimeError(
            "Migration 0035 stopped without skipping invalid role data. "
            "Correct these users.roles/users.role values, then retry:\n"
            + details
            + suffix
        )
    return assignments


def upgrade() -> None:
    bind = op.get_bind()
    app_role_name = _application_role_name()
    app_role = _quoted_role(bind, app_role_name)
    _ensure_runtime_role_is_restricted(bind, app_role_name)
    _ensure_roles_table_owner(bind)
    backfill = _validated_backfill(bind)

    if bind.dialect.name == "postgresql":
        has_public_usage = bind.execute(
            sa.text("SELECT has_schema_privilege(:role_name, 'public', 'USAGE')"),
            {"role_name": app_role_name},
        ).scalar_one()
        if not has_public_usage:
            raise RuntimeError(
                f"Application database role {app_role_name!r} needs USAGE on schema public."
            )

    op.create_table(
        "user_role_assignments",
        sa.Column("assignment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_user_role_assignments_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("assignment_id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role_assignments_user_role"),
    )
    op.create_index("ix_user_role_assignments_user_id", "user_role_assignments", ["user_id"])
    op.create_index("ix_user_role_assignments_role_id", "user_role_assignments", ["role_id"])

    op.create_table(
        "user_role_assignment_history",
        sa.Column("history_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("previous_active_role_id", sa.Integer(), nullable=True),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('assigned', 'revoked', 'reactivated', 'legacy_backfill', 'active_role_changed')",
            name="ck_user_role_assignment_history_event_type",
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["user_role_assignments.assignment_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_active_role_id"], ["roles.role_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("history_id"),
    )
    op.create_index(
        "ix_user_role_assignment_history_assignment_id",
        "user_role_assignment_history",
        ["assignment_id"],
    )

    assignment_table = sa.table(
        "user_role_assignments",
        sa.column("assignment_id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("role_id", sa.Integer),
        sa.column("created_by", sa.Integer),
        sa.column("updated_by", sa.Integer),
        sa.column("status", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    history_table = sa.table(
        "user_role_assignment_history",
        sa.column("assignment_id", sa.Integer),
        sa.column("event_type", sa.String),
        sa.column("previous_active_role_id", sa.Integer),
        sa.column("changed_by", sa.Integer),
        sa.column("changed_at", sa.DateTime(timezone=True)),
    )
    for user_id, _role_name, role_id in backfill:
        assignment_id = bind.execute(
            sa.insert(assignment_table)
            .values(
                user_id=user_id,
                role_id=role_id,
                created_by=None,
                updated_by=None,
                status="active",
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
            .returning(assignment_table.c.assignment_id)
        ).scalar_one()
        bind.execute(
            sa.insert(history_table).values(
                assignment_id=assignment_id,
                event_type="legacy_backfill",
                previous_active_role_id=None,
                changed_by=None,
                changed_at=sa.func.now(),
            )
        )

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"GRANT SELECT ON TABLE public.roles TO {app_role}"
        )
        op.execute(
            f"CREATE POLICY {ROLES_POLICY} ON public.roles "
            f"FOR SELECT TO {app_role} USING (true)"
        )

        op.execute(
            "ALTER TABLE public.user_role_assignments ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            "ALTER TABLE public.user_role_assignment_history ENABLE ROW LEVEL SECURITY"
        )
        for table_name in ("user_role_assignments", "user_role_assignment_history"):
            op.execute(
                f"REVOKE ALL ON TABLE public.{table_name} "
                "FROM anon, authenticated, service_role"
            )
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON TABLE public.user_role_assignments TO {app_role}"
        )
        op.execute(
            f"GRANT SELECT, INSERT ON TABLE public.user_role_assignment_history TO {app_role}"
        )
        op.execute(
            f"GRANT USAGE, SELECT ON SEQUENCE public.user_role_assignments_assignment_id_seq TO {app_role}"
        )
        op.execute(
            f"GRANT USAGE, SELECT ON SEQUENCE public.user_role_assignment_history_history_id_seq TO {app_role}"
        )
        op.execute(
            f"CREATE POLICY {ASSIGNMENTS_SELECT_POLICY} ON public.user_role_assignments "
            f"FOR SELECT TO {app_role} USING (true)"
        )
        op.execute(
            f"CREATE POLICY {ASSIGNMENTS_INSERT_POLICY} ON public.user_role_assignments "
            f"FOR INSERT TO {app_role} WITH CHECK (true)"
        )
        op.execute(
            f"CREATE POLICY {ASSIGNMENTS_UPDATE_POLICY} ON public.user_role_assignments "
            f"FOR UPDATE TO {app_role} USING (true) WITH CHECK (true)"
        )
        op.execute(
            f"CREATE POLICY {HISTORY_SELECT_POLICY} ON public.user_role_assignment_history "
            f"FOR SELECT TO {app_role} USING (true)"
        )
        op.execute(
            f"CREATE POLICY {HISTORY_INSERT_POLICY} ON public.user_role_assignment_history "
            f"FOR INSERT TO {app_role} WITH CHECK (true)"
        )

        op.execute(
            """
            CREATE FUNCTION public.campus_kart_0035_prevent_buyer_deactivation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE role_name_value text;
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    SELECT role_name INTO role_name_value
                    FROM public.roles WHERE role_id = NEW.role_id;
                    IF role_name_value = 'buyer' AND NEW.status <> 'active' THEN
                        RAISE EXCEPTION 'Buyer role assignments must be active';
                    END IF;
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    IF NEW.user_id IS DISTINCT FROM OLD.user_id
                       OR NEW.role_id IS DISTINCT FROM OLD.role_id THEN
                        RAISE EXCEPTION 'An assignment user_id or role_id cannot be changed';
                    END IF;
                    SELECT role_name INTO role_name_value
                    FROM public.roles WHERE role_id = NEW.role_id;
                    IF role_name_value = 'buyer' AND NEW.status <> 'active' THEN
                        RAISE EXCEPTION 'Buyer role assignments cannot be deactivated';
                    END IF;
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    SELECT role_name INTO role_name_value
                    FROM public.roles WHERE role_id = OLD.role_id;
                    IF role_name_value = 'buyer' THEN
                        RAISE EXCEPTION 'Buyer role assignments cannot be deleted';
                    END IF;
                    RETURN OLD;
                END IF;
                RAISE EXCEPTION 'Unsupported operation % for buyer assignment guard', TG_OP;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER campus_kart_0035_buyer_assignment_guard
            BEFORE INSERT OR UPDATE OR DELETE ON public.user_role_assignments
            FOR EACH ROW
            EXECUTE FUNCTION public.campus_kart_0035_prevent_buyer_deactivation()
            """
        )
        op.execute(
            """
            CREATE FUNCTION public.campus_kart_0035_reject_history_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'user_role_assignment_history is append-only';
                RETURN NULL;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER campus_kart_0035_history_no_update_delete
            BEFORE UPDATE OR DELETE ON public.user_role_assignment_history
            FOR EACH ROW
            EXECUTE FUNCTION public.campus_kart_0035_reject_history_mutation()
            """
        )
        op.execute(
            """
            CREATE TRIGGER campus_kart_0035_history_no_truncate
            BEFORE TRUNCATE ON public.user_role_assignment_history
            FOR EACH STATEMENT
            EXECUTE FUNCTION public.campus_kart_0035_reject_history_mutation()
            """
        )


def _policy_role_name(bind) -> str | None:
    return bind.execute(
        sa.text(
            """
            SELECT roles.rolname
            FROM pg_policy AS policy
            JOIN pg_roles AS roles ON roles.oid = ANY(policy.polroles)
            WHERE policy.polrelid = to_regclass('public.roles')
              AND policy.polname = :policy_name
            """
        ),
        {"policy_name": ROLES_POLICY},
    ).scalar_one_or_none()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Read the role stored in our own policy so downgrade does not depend on
        # the current DATABASE_URL username being unchanged since upgrade.
        app_role_name = _policy_role_name(bind)
        if app_role_name:
            app_role = _quoted_role(bind, app_role_name)
            op.execute(f"REVOKE SELECT ON TABLE public.roles FROM {app_role}")

        op.execute(
            "DROP TRIGGER IF EXISTS campus_kart_0035_history_no_truncate "
            "ON public.user_role_assignment_history"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS campus_kart_0035_history_no_update_delete "
            "ON public.user_role_assignment_history"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS public.campus_kart_0035_reject_history_mutation()"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS campus_kart_0035_buyer_assignment_guard "
            "ON public.user_role_assignments"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS public.campus_kart_0035_prevent_buyer_deactivation()"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {HISTORY_INSERT_POLICY} "
            "ON public.user_role_assignment_history"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {HISTORY_SELECT_POLICY} "
            "ON public.user_role_assignment_history"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {ASSIGNMENTS_UPDATE_POLICY} ON public.user_role_assignments"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {ASSIGNMENTS_INSERT_POLICY} ON public.user_role_assignments"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {ASSIGNMENTS_SELECT_POLICY} ON public.user_role_assignments"
        )
        op.execute(f"DROP POLICY IF EXISTS {ROLES_POLICY} ON public.roles")
        op.execute(
            "ALTER TABLE public.user_role_assignment_history DISABLE ROW LEVEL SECURITY"
        )
        op.execute(
            "ALTER TABLE public.user_role_assignments DISABLE ROW LEVEL SECURITY"
        )
        # Migration 0034 creates roles without RLS; restore that baseline.
        op.execute("ALTER TABLE public.roles DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_user_role_assignment_history_assignment_id",
        table_name="user_role_assignment_history",
    )
    op.drop_table("user_role_assignment_history")
    op.drop_index("ix_user_role_assignments_role_id", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_user_id", table_name="user_role_assignments")
    op.drop_table("user_role_assignments")
