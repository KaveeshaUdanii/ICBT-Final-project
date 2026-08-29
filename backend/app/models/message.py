from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Message(Base):
    """A lightweight comment thread scoped to one Purchase Order or Shipment, so a delay or
    spec question is logged in-app between a supplier and internal staff instead of over email
    (targets the "communication breakdowns between suppliers and merchandisers" problem)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # purchase_order | shipment
    entity_id: Mapped[int] = mapped_column()

    sender_user_id: Mapped[int] = mapped_column()
    sender_name: Mapped[str] = mapped_column(String(120))
    sender_role: Mapped[str] = mapped_column(String(30))

    body: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
