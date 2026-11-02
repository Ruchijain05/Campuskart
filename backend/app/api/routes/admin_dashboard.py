from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.admin_dashboard import AdminDashboardRead
from app.services.admin_dashboard import get_admin_dashboard

router = APIRouter(prefix="/admin/dashboard", tags=["admin dashboard"])


@router.get("", response_model=AdminDashboardRead)
def read_admin_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminDashboardRead:
    return get_admin_dashboard(db)
