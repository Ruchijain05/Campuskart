from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    kind: str,
    title: str,
    message: str,
    link: str | None = None,
) -> None:
    db.add(Notification(user_id=user_id, kind=kind, title=title, message=message, link=link))


def list_notifications(db: Session, user_id: int) -> tuple[list[Notification], int]:
    rows = list(db.scalars(
        select(Notification).where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(100)
    ).all())
    unread = db.scalar(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    ) or 0
    return rows, unread


def unread_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    ) or 0


def mark_read(db: Session, user_id: int, notification_id: int | None = None) -> bool:
    query = update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
    if notification_id is not None:
        query = query.where(Notification.id == notification_id)
    result = db.execute(query.values(is_read=True))
    db.commit()
    return result.rowcount > 0
