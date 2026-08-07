from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PurchaseOrderStatus


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    supplier = relationship("Supplier", back_populates="purchase_orders")

    raw_material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"), nullable=False)
    raw_material = relationship("RawMaterial")

    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)

    order_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, native_enum=False, length=20), default=PurchaseOrderStatus.DRAFT
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    risk_flag: Mapped[bool] = mapped_column(default=False)
    risk_notes: Mapped[str] = mapped_column(String(500), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    shipments = relationship("Shipment", back_populates="purchase_order")

    @property
    def total_value(self) -> float:
        return round(self.quantity * self.unit_price, 2)
