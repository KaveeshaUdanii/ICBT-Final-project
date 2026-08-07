from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import NotificationSeverity


class Notification(Base):
    """Notification System (module 12)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = broadcast to all
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(String(500))
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False, length=20), default=NotificationSeverity.INFO
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(60), default="system")  # system | smart_contract | ai_engine
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
