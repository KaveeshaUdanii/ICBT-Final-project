from datetime import date, datetime

from pydantic import ConfigDict, BaseModel, Field

from app.models.enums import ShipmentStatus


class ShipmentBase(BaseModel):
    shipment_code: str = Field(min_length=2, max_length=40)
    supplier_id: int
    purchase_order_id: int | None = None
    origin: str = ""
    destination: str = "Colombo, Sri Lanka"
    quantity: float = Field(default=0.0, ge=0)
    expected_delivery_date: date


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentUpdate(BaseModel):
    origin: str | None = None
    destination: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    expected_delivery_date: date | None = None
    actual_delivery_date: date | None = None
    status: ShipmentStatus | None = None


class ShipmentRead(ShipmentBase):
    id: int
    order_date: date
    actual_delivery_date: date | None
    status: ShipmentStatus
    predicted_delay_days: float | None
    delay_probability: float | None
    is_anomaly: bool
    anomaly_score: float | None
    actual_delay_days: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
