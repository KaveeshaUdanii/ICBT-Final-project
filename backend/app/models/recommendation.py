from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recommendation(Base):
    """Output of the Intelligent Recommendation Engine (module 7)."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40))  # supplier | shipment | raw_material | purchase_order
    entity_id: Mapped[int] = mapped_column()
    recommendation_text: Mapped[str] = mapped_column(String(500))
    recommended_supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
