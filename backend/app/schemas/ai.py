from datetime import datetime

from pydantic import ConfigDict, BaseModel


class FeatureContribution(BaseModel):
    feature: str
    label: str
    value: float
    display_value: str
    typical_display_value: str
    contribution: float
    direction: str  # "increases_risk" | "decreases_risk"
    explanation: str


class ExplanationResult(BaseModel):
    model_name: str
    base_value: float
    prediction: float
    top_factors: list[FeatureContribution]
    plain_language_summary: str


class DelayPredictionResult(BaseModel):
    shipment_id: int
    predicted_delay_days: float
    delay_probability: float
    is_anomaly: bool
    anomaly_score: float
    explanation: ExplanationResult


class SupplierRiskResult(BaseModel):
    supplier_id: int
    risk_score: float
    risk_level: str
    explanation: ExplanationResult


class DemandForecastResult(BaseModel):
    raw_material_id: int
    predicted_demand_next_30_days: float
    explanation: ExplanationResult


class StockoutRiskResult(BaseModel):
    raw_material_id: int
    stockout_risk_probability: float
    predicted_demand_next_30_days: float
    explanation: ExplanationResult


class RiskPredictionRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    model_name: str
    prediction_value: float
    probability: float | None
    explanation: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    recommendation_text: str
    recommended_supplier_id: int | None
    confidence: float
    is_dismissed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
