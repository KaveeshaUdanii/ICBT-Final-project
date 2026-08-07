from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskPrediction(Base):
    """Stores every output produced by the AI Risk Prediction Engine (module 6)."""

    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40))  # supplier | shipment | purchase_order
    entity_id: Mapped[int] = mapped_column()
    model_name: Mapped[str] = mapped_column(String(60))  # delay_prediction | supplier_risk_scoring | anomaly_detection
    prediction_value: Mapped[float] = mapped_column(Float, default=0.0)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
