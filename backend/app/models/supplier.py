from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(180), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(40), default="")
    country: Mapped[str] = mapped_column(String(80), default="Sri Lanka")
    category: Mapped[str] = mapped_column(String(80), default="fabric")

    # Performance metrics used as ML features
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, default=0.9)  # 0-1
    defect_rate: Mapped[float] = mapped_column(Float, default=0.02)  # 0-1
    cancellation_rate: Mapped[float] = mapped_column(Float, default=0.02)  # 0-1
    avg_lead_time_days: Mapped[float] = mapped_column(Float, default=14.0)
    order_volume_last_year: Mapped[int] = mapped_column(default=50)

    # AI-derived fields
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, native_enum=False, length=10), default=RiskLevel.LOW)
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    raw_materials = relationship("RawMaterial", back_populates="supplier", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="supplier", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier", cascade="all, delete-orphan")
