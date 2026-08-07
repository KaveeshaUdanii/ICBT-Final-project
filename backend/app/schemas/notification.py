from datetime import datetime

from pydantic import ConfigDict, BaseModel

from app.models.enums import NotificationSeverity


class NotificationRead(BaseModel):
    id: int
    user_id: int | None
    title: str
    message: str
    severity: NotificationSeverity
    related_entity_type: str | None
    related_entity_id: int | None
    is_read: bool
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
