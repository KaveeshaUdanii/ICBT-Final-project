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
    # Agreed SLA term: percent of order value charged per day late. 0 = no penalty clause.
    penalty_rate_pct: float = Field(default=0.0, ge=0, le=100)


class PurchaseOrderCreate(PurchaseOrderBase):
    pass


class PurchaseOrderUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    expected_delivery_date: date | None = None
    status: PurchaseOrderStatus | None = None
    penalty_rate_pct: float | None = Field(default=None, ge=0, le=100)


class PurchaseOrderRespond(BaseModel):
    """Supplier's accept/decline response to a PO -- the single biggest thing that turns the
    portal from a read-only viewer into something the supplier actually acts on."""

    response: str = Field(pattern="^(accepted|declined)$")
    reason: str = Field(default="", max_length=300)


class PurchaseOrderRead(PurchaseOrderBase):
    id: int
    order_date: date
    status: PurchaseOrderStatus
    approved_by: int | None
    risk_flag: bool
    risk_notes: str
    total_value: float
    supplier_response: str
    decline_reason: str
    penalty_exposure: float | None
    data_entry_flag: bool
    data_entry_warning: str
    # Denormalized from the raw_material relationship so callers never need a second request
    # (or, for a Supplier account, access to the staff-only Raw Materials catalog endpoint)
    # just to know what material their own purchase order is for. Populated by the router.
    raw_material_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderExternalRead(PurchaseOrderBase):
    """What a Supplier-portal account may see of its own purchase orders. Omits risk_flag and
    risk_notes -- the smart-contract engine's internal auto-flagging notes, which can read
    e.g. "Auto-flagged: supplier 'X' is HIGH risk (score Y%)" and would hand the supplier
    exactly the internal risk judgment being made about them. approved_by (an internal user
    id) is omitted too -- it identifies internal staff and carries no value to the supplier.
    supplier_response/penalty_exposure/data_entry_warning are kept: these are contractual
    terms and facts about this specific order, not an internal judgment about the supplier."""

    id: int
    order_date: date
    status: PurchaseOrderStatus
    total_value: float
    supplier_response: str
    decline_reason: str
    penalty_exposure: float | None
    data_entry_flag: bool
    data_entry_warning: str
    raw_material_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
