from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Blockchain Audit Trail (module 15): human-readable view over the block ledger."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    performed_by: Mapped[str] = mapped_column(String(120), default="system")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    block_id: Mapped[int | None] = mapped_column(ForeignKey("blocks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
