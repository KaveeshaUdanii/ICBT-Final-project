from datetime import datetime

from pydantic import ConfigDict, BaseModel, Field

from app.models.enums import MaterialCategory


class RawMaterialBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: MaterialCategory = MaterialCategory.FABRIC
    unit: str = "kg"
    quantity_on_hand: float = Field(default=0.0, ge=0)
    reorder_level: float = Field(default=100.0, ge=0)
    unit_cost: float = Field(default=1.0, ge=0)
    lead_time_days: int = Field(default=14, ge=0)
    supplier_id: int


class RawMaterialCreate(RawMaterialBase):
    pass


class RawMaterialUpdate(BaseModel):
    name: str | None = None
    category: MaterialCategory | None = None
    unit: str | None = None
    quantity_on_hand: float | None = Field(default=None, ge=0)
    reorder_level: float | None = Field(default=None, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    supplier_id: int | None = None


class RawMaterialRead(RawMaterialBase):
    id: int
    needs_reorder: bool
    predicted_demand_next_30_days: float | None = None
    stockout_risk_probability: float | None = None
    last_forecasted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
