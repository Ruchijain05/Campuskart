from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.models.notification import Notification
from app.schemas.notifications import NotificationRead, NotificationSummary
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationSummary)
def list_notifications(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> NotificationSummary:
    notifications, unread = notification_service.list_notifications(db, buyer.id)
    return NotificationSummary(notifications=notifications, unread_count=unread)


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict[str, int]:
    return {"unread_count": notification_service.unread_count(db, buyer.id)}


@router.patch("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> Response:
    notification_service.mark_read(db, buyer.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> NotificationRead:
    row = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == buyer.id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification_service.mark_read(db, buyer.id, notification_id)
    db.refresh(row)
    return row
