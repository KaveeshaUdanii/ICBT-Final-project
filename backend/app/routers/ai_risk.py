from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import predict as ai_predict
from app.ai.explain import explain_instance
from app.ai.features import (
    FEATURES_ANOMALY,
    FEATURES_DELAY,
    FEATURES_DEMAND,
    FEATURES_RISK,
    FEATURES_STOCKOUT,
    build_anomaly_features,
    build_delay_features,
    build_demand_features,
    build_risk_features,
    build_stockout_features,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_manager_or_admin, require_staff
from app.models.enums import RiskLevel
from app.models.raw_material import RawMaterial
from app.models.risk_prediction import RiskPrediction
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.ai import (
    DelayPredictionResult,
    DemandForecastResult,
    ExplanationResult,
    RiskPredictionRead,
    StockoutRiskResult,
    SupplierRiskResult,
)
from app.services import recommendation_service, smart_contract_service

router = APIRouter(prefix="/api/ai", tags=["AI Risk Prediction Engine & Explainable AI"])


def _risk_level_from_score(score: float) -> RiskLevel:
    if score >= 70:
        return RiskLevel.HIGH
    if score >= 40:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _score_supplier(db: Session, supplier: Supplier) -> SupplierRiskResult:
    if not ai_predict.models_are_trained():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI models are not yet trained.")

    features = build_risk_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, supplier.order_volume_last_year,
    )
    score = ai_predict.score_supplier_features(features)
    level = _risk_level_from_score(score)

    supplier.risk_score = round(score, 2)
    supplier.risk_level = level
    supplier.last_scored_at = datetime.now(timezone.utc)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    explanation = explain_instance(
        model_name="supplier_risk_scoring",
        stats_key="risk",
        instance=features,
        feature_order=FEATURES_RISK,
        predict_fn=lambda X: ai_predict.risk_predict_proba(X) * 100,
    )

    db.add(
        RiskPrediction(
            entity_type="supplier",
            entity_id=supplier.id,
            model_name="supplier_risk_scoring",
            prediction_value=supplier.risk_score,
            probability=supplier.risk_score / 100,
            explanation=explanation,
        )
    )
    db.commit()

    smart_contract_service.evaluate_supplier_risk(db, supplier)
    if level == RiskLevel.HIGH:
        recommendation_service.recommend_alternative_suppliers(db, supplier)

    return SupplierRiskResult(
        supplier_id=supplier.id,
        risk_score=supplier.risk_score,
        risk_level=level.value,
        explanation=ExplanationResult(**explanation),
    )


@router.post("/suppliers/{supplier_id}/score", response_model=SupplierRiskResult)
def score_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return _score_supplier(db, supplier)


@router.post("/suppliers/score-all", response_model=list[SupplierRiskResult])
def score_all_suppliers(db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    suppliers = db.execute(select(Supplier).where(Supplier.is_active.is_(True))).scalars().all()
    return [_score_supplier(db, s) for s in suppliers]


def _predict_shipment(db: Session, shipment: Shipment) -> DelayPredictionResult:
    if not ai_predict.models_are_trained():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI models are not yet trained.")

    supplier = shipment.supplier
    delay_features = build_delay_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, shipment.quantity, shipment.order_date,
        shipment.expected_delivery_date, supplier.order_volume_last_year,
    )
    delay_days, delay_prob = ai_predict.score_delay_features(delay_features)

    requested_lead = max((shipment.expected_delivery_date - shipment.order_date).days, 1)
    anomaly_features = build_anomaly_features(
        shipment.quantity, requested_lead, supplier.on_time_delivery_rate,
        supplier.defect_rate, supplier.cancellation_rate, shipment.expected_delivery_date,
    )
    is_anomaly, anomaly_score = ai_predict.score_anomaly_features(anomaly_features)

    shipment.predicted_delay_days = round(delay_days, 2)
    shipment.delay_probability = round(delay_prob, 4)
    shipment.is_anomaly = is_anomaly
    shipment.anomaly_score = round(anomaly_score, 4)
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    explanation = explain_instance(
        model_name="delay_prediction",
        stats_key="delay",
        instance=delay_features,
        feature_order=FEATURES_DELAY,
        predict_fn=lambda X: ai_predict.delay_predict_proba(X),
    )

    db.add_all(
        [
            RiskPrediction(
                entity_type="shipment", entity_id=shipment.id, model_name="delay_prediction",
                prediction_value=shipment.predicted_delay_days, probability=shipment.delay_probability,
                explanation=explanation,
            ),
            RiskPrediction(
                entity_type="shipment", entity_id=shipment.id, model_name="anomaly_detection",
                prediction_value=float(is_anomaly), probability=shipment.anomaly_score,
                explanation={"note": "Unsupervised Isolation Forest score; higher = more anomalous."},
            ),
        ]
    )
    db.commit()

    smart_contract_service.evaluate_shipment_prediction(db, shipment)

    return DelayPredictionResult(
        shipment_id=shipment.id,
        predicted_delay_days=shipment.predicted_delay_days,
        delay_probability=shipment.delay_probability,
        is_anomaly=shipment.is_anomaly,
        anomaly_score=shipment.anomaly_score,
        explanation=ExplanationResult(**explanation),
    )


@router.post("/shipments/{shipment_id}/predict", response_model=DelayPredictionResult)
def predict_shipment(shipment_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    return _predict_shipment(db, shipment)


@router.post("/shipments/predict-all", response_model=list[DelayPredictionResult])
def predict_all_shipments(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    shipments = (
        db.execute(select(Shipment).where(Shipment.status.in_(["pending", "in_transit"]))).scalars().all()
    )
    return [_predict_shipment(db, s) for s in shipments]


def _forecast_demand(db: Session, material: RawMaterial) -> tuple[DemandForecastResult, dict]:
    """Returns the result plus the raw feature dict, so _predict_stockout can reuse the
    same forecast as one of its own input features without recomputing it."""
    if not ai_predict.models_are_trained():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI models are not yet trained.")

    features = build_demand_features(
        material.quantity_on_hand,
        material.reorder_level,
        material.unit_cost,
        material.lead_time_days,
        material.supplier.on_time_delivery_rate,
        date.today(),
    )
    predicted_demand = ai_predict.score_demand_features(features)

    material.predicted_demand_next_30_days = round(predicted_demand, 2)
    material.last_forecasted_at = datetime.now(timezone.utc)
    db.add(material)
    db.commit()
    db.refresh(material)

    explanation = explain_instance(
        model_name="demand_forecasting",
        stats_key="demand",
        instance=features,
        feature_order=FEATURES_DEMAND,
        predict_fn=lambda X: ai_predict.demand_predict(X),
        higher_is_worse=False,
    )
    db.add(
        RiskPrediction(
            entity_type="raw_material", entity_id=material.id, model_name="demand_forecasting",
            prediction_value=material.predicted_demand_next_30_days, probability=None, explanation=explanation,
        )
    )
    db.commit()

    return (
        DemandForecastResult(
            raw_material_id=material.id,
            predicted_demand_next_30_days=material.predicted_demand_next_30_days,
            explanation=ExplanationResult(**explanation),
        ),
        features,
    )


def _predict_stockout(db: Session, material: RawMaterial) -> StockoutRiskResult:
    demand_result, _ = _forecast_demand(db, material)

    features = build_stockout_features(
        material.quantity_on_hand,
        material.reorder_level,
        material.lead_time_days,
        material.supplier.on_time_delivery_rate,
        date.today(),
        demand_result.predicted_demand_next_30_days,
    )
    risk_proba = ai_predict.score_stockout_features(features)

    material.stockout_risk_probability = round(risk_proba, 4)
    db.add(material)
    db.commit()
    db.refresh(material)

    explanation = explain_instance(
        model_name="stockout_risk",
        stats_key="stockout",
        instance=features,
        feature_order=FEATURES_STOCKOUT,
        predict_fn=lambda X: ai_predict.stockout_predict_proba(X),
    )
    db.add(
        RiskPrediction(
            entity_type="raw_material", entity_id=material.id, model_name="stockout_risk",
            prediction_value=material.stockout_risk_probability, probability=material.stockout_risk_probability,
            explanation=explanation,
        )
    )
    db.commit()

    smart_contract_service.evaluate_stockout_risk(db, material)

    return StockoutRiskResult(
        raw_material_id=material.id,
        stockout_risk_probability=material.stockout_risk_probability,
        predicted_demand_next_30_days=demand_result.predicted_demand_next_30_days,
        explanation=ExplanationResult(**explanation),
    )


@router.post("/raw-materials/{material_id}/forecast-demand", response_model=DemandForecastResult)
def forecast_demand(material_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found.")
    result, _ = _forecast_demand(db, material)
    return result


@router.post("/raw-materials/forecast-all", response_model=list[DemandForecastResult])
def forecast_all_demand(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    materials = db.execute(select(RawMaterial)).scalars().all()
    return [_forecast_demand(db, m)[0] for m in materials]


@router.post("/raw-materials/{material_id}/predict-stockout", response_model=StockoutRiskResult)
def predict_stockout(material_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found.")
    return _predict_stockout(db, material)


@router.post("/raw-materials/predict-stockout-all", response_model=list[StockoutRiskResult])
def predict_all_stockout(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    materials = db.execute(select(RawMaterial)).scalars().all()
    return [_predict_stockout(db, m) for m in materials]


@router.get("/predictions", response_model=list[RiskPredictionRead])
def list_predictions(
    entity_type: str | None = None,
    entity_id: int | None = None,
    model_name: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    stmt = select(RiskPrediction).order_by(RiskPrediction.id.desc())
    if entity_type:
        stmt = stmt.where(RiskPrediction.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(RiskPrediction.entity_id == entity_id)
    if model_name:
        stmt = stmt.where(RiskPrediction.model_name == model_name)
    return db.execute(stmt.limit(limit)).scalars().all()


@router.get("/model-performance")
def model_performance(_: User = Depends(require_staff)):
    report_path = settings.ML_MODELS_DIR / "training_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Models have not been trained yet.")
    import json

    with open(report_path) as f:
        return json.load(f)
