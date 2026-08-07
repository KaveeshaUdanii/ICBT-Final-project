from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ShipmentStatus


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    supplier = relationship("Supplier", back_populates="shipments")

    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    purchase_order = relationship("PurchaseOrder", back_populates="shipments")

    origin: Mapped[str] = mapped_column(String(120), default="")
    destination: Mapped[str] = mapped_column(String(120), default="Colombo, Sri Lanka")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)

    order_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, native_enum=False, length=20), default=ShipmentStatus.PENDING
    )

    # AI Risk Prediction Engine outputs
    predicted_delay_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    delay_probability: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def actual_delay_days(self) -> int | None:
        if self.actual_delivery_date is None:
            return None
        return (self.actual_delivery_date - self.expected_delivery_date).days
