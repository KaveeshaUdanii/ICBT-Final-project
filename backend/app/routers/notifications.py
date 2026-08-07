from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import UserRole
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead

router = APIRouter(prefix="/api/notifications", tags=["Notification System"])


def _visible_to(user: User):
    """Internal staff see broadcast alerts (user_id is null) plus anything addressed to
    them directly. A Supplier account is external, so it must NEVER see broadcast staff
    alerts (e.g. "Supplier X auto-flagged high-risk") -- only notifications explicitly
    targeted at its own linked user account."""
    if user.role == UserRole.SUPPLIER:
        return Notification.user_id == user.id
    return (Notification.user_id.is_(None)) | (Notification.user_id == user.id)


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Notification).where(_visible_to(current_user)).order_by(Notification.id.desc())
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return db.execute(stmt.limit(limit)).scalars().all()


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Notification).where(_visible_to(current_user), Notification.is_read.is_(False))
    count = len(db.execute(stmt).scalars().all())
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notification = db.get(Notification, notification_id)
    if not notification or (current_user.role == UserRole.SUPPLIER and notification.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notification.is_read = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Notification).where(_visible_to(current_user), Notification.is_read.is_(False))
    notifications = db.execute(stmt).scalars().all()
    for n in notifications:
        n.is_read = True
        db.add(n)
    db.commit()
    return {"marked_read": len(notifications)}
