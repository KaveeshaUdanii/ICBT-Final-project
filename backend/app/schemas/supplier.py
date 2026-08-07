from datetime import datetime

from pydantic import ConfigDict, BaseModel, EmailStr, Field

from app.models.enums import RiskLevel


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr
    contact_phone: str = ""
    country: str = "Sri Lanka"
    category: str = "fabric"
    on_time_delivery_rate: float = Field(default=0.9, ge=0, le=1)
    defect_rate: float = Field(default=0.02, ge=0, le=1)
    cancellation_rate: float = Field(default=0.02, ge=0, le=1)
    avg_lead_time_days: float = Field(default=14.0, ge=0)
    order_volume_last_year: int = Field(default=50, ge=0)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    country: str | None = None
    category: str | None = None
    on_time_delivery_rate: float | None = Field(default=None, ge=0, le=1)
    defect_rate: float | None = Field(default=None, ge=0, le=1)
    cancellation_rate: float | None = Field(default=None, ge=0, le=1)
    avg_lead_time_days: float | None = Field(default=None, ge=0)
    order_volume_last_year: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SupplierRead(SupplierBase):
    id: int
    risk_score: float
    risk_level: RiskLevel
    last_scored_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
