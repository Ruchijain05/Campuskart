from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.role import Role
from app.models.user_role_map import UserRoleMap


def get_role_id(db: Session, role: UserRole) -> int:
    role_id = db.scalar(select(Role.role_id).where(Role.role_name == role.value))
    if role_id is None:
        raise RuntimeError(f"Role {role.value!r} is missing from role_master.")
    return role_id


def grant_role(db: Session, user: User, role: UserRole, *, actor_id: int | None = None) -> None:
    role_id = get_role_id(db, role)
    existing = db.scalar(
        select(UserRoleMap.id).where(
            UserRoleMap.user_id == user.id,
            UserRoleMap.role_id == role_id,
        )
    )
    if existing is None:
        user.role_assignments.append(
            UserRoleMap(user_id=user.id, role_id=role_id, created_by=actor_id, updated_by=actor_id)
        )
