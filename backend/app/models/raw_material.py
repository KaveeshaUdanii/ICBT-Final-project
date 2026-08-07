from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MaterialCategory


class RawMaterial(Base):
    __tablename__ = "raw_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[MaterialCategory] = mapped_column(
        Enum(MaterialCategory, native_enum=False, length=20), default=MaterialCategory.FABRIC
    )
    unit: Mapped[str] = mapped_column(String(20), default="kg")

    quantity_on_hand: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_level: Mapped[float] = mapped_column(Float, default=100.0)
    unit_cost: Mapped[float] = mapped_column(Float, default=1.0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14)

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    supplier = relationship("Supplier", back_populates="raw_materials")

    # Demand Forecasting Model + Inventory Stockout Risk Model outputs (additions beyond
    # the proposal's 3 required models -- see app/ai/train.py).
    predicted_demand_next_30_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    stockout_risk_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_forecasted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def needs_reorder(self) -> bool:
        return self.quantity_on_hand <= self.reorder_level
