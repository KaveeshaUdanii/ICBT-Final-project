from sqlalchemy.orm import Session

from app.models.enums import NotificationSeverity
from app.models.notification import Notification


def create_notification(
    db: Session,
    title: str,
    message: str,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    user_id: int | None = None,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    source: str = "system",
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        source=source,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
