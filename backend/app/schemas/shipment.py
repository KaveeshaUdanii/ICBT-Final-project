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


class ShipmentShip(BaseModel):
    """Supplier marking their own shipment as sent -- splits the workflow the way it actually
    works between two organizations, instead of only internal staff ever touching status."""

    carrier: str = Field(default="", max_length=120)
    tracking_number: str = Field(default="", max_length=120)


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
    carrier: str
    tracking_number: str
    supplier_confirmed_delivery: bool
    supplier_confirmed_delivery_at: datetime | None
    staff_confirmed_delivery: bool
    staff_confirmed_delivery_at: datetime | None
    data_entry_flag: bool
    data_entry_warning: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShipmentExternalRead(ShipmentBase):
    """What a Supplier-portal account may see of its own shipments. Omits
    predicted_delay_days/delay_probability (the AI Delay Prediction Model's output) and
    is_anomaly/anomaly_score (the Anomaly Detection Model's flag) -- both are internal risk
    signals the company uses to decide how to treat a supplier, not something to hand back to
    the supplier being scored. actual_delay_days is kept: once a shipment is delivered, it's
    a plain factual fact (expected date vs. actual date), not an AI judgment. carrier/tracking
    and the delivery-confirmation flags are the supplier's own inputs/actions, kept in full."""

    id: int
    order_date: date
    actual_delivery_date: date | None
    status: ShipmentStatus
    actual_delay_days: int | None = None
    carrier: str
    tracking_number: str
    supplier_confirmed_delivery: bool
    supplier_confirmed_delivery_at: datetime | None
    staff_confirmed_delivery: bool
    staff_confirmed_delivery_at: datetime | None
    data_entry_flag: bool
    data_entry_warning: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
