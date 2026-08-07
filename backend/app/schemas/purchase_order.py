from datetime import date, datetime

from pydantic import ConfigDict, BaseModel, Field

from app.models.enums import PurchaseOrderStatus


class PurchaseOrderBase(BaseModel):
    po_number: str = Field(min_length=2, max_length=40)
    supplier_id: int
    raw_material_id: int
    quantity: float = Field(default=0.0, ge=0)
    unit_price: float = Field(default=0.0, ge=0)
    expected_delivery_date: date


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class PurchaseOrderUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    expected_delivery_date: date | None = None
    status: PurchaseOrderStatus | None = None


class PurchaseOrderRead(PurchaseOrderBase):
    id: int
    order_date: date
    status: PurchaseOrderStatus
    approved_by: int | None
    risk_flag: bool
    risk_notes: str
    total_value: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
