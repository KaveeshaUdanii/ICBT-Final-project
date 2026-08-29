from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """A file (compliance certificate, spec sheet, invoice...) attached to a Purchase Order or
    Shipment. Its content hash is anchored on the blockchain ledger at upload time (see
    document_service.py), so a disputed paper document can later be verified against an
    immutable record of exactly what was uploaded and when -- closing the "difficult to verify
    facts about historical records" gap the proposal identifies as a case for blockchain."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # purchase_order | shipment
    entity_id: Mapped[int] = mapped_column()

    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))

    uploaded_by_user_id: Mapped[int] = mapped_column()
    uploaded_by_name: Mapped[str] = mapped_column(String(120))

    block_id: Mapped[int | None] = mapped_column(ForeignKey("blocks.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
