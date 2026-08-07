"""Scenario Simulation (module 13): what-if analysis for supplier failure, demand spikes,
lead-time increases, and raw-material shortages. Re-runs the real trained AI models on
hypothetically modified inputs rather than returning canned numbers."""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai import predict as ai_predict
from app.ai.features import build_delay_features, build_risk_features
from app.models.enums import ScenarioType
from app.models.raw_material import RawMaterial
from app.models.supplier import Supplier
from app.services.production_impact_service import estimate_production_impact


def _require_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not exist.")
    return supplier


def _require_material(db: Session, material_id: int) -> RawMaterial:
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Raw material does not exist.")
    return material


def simulate_supplier_failure(db: Session, params: dict) -> dict:
    supplier = _require_supplier(db, int(params["supplier_id"]))
    severity = float(params.get("severity", 0.6))  # 0-1: how badly the supplier degrades

    baseline_features = build_risk_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, supplier.order_volume_last_year,
    )
    baseline_score = ai_predict.score_supplier_features(baseline_features)

    degraded_features = build_risk_features(
        on_time_delivery_rate=max(supplier.on_time_delivery_rate * (1 - severity), 0.05),
        defect_rate=min(supplier.defect_rate + 0.15 * severity, 0.9),
        cancellation_rate=min(supplier.cancellation_rate + 0.20 * severity, 0.9),
        avg_lead_time_days=supplier.avg_lead_time_days * (1 + severity),
        order_volume_last_year=supplier.order_volume_last_year,
    )
    degraded_score = ai_predict.score_supplier_features(degraded_features)

    affected_materials = len(supplier.raw_materials)
    affected_shipments = len(supplier.shipments)

    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "severity_applied": severity,
        "baseline_risk_score": round(baseline_score, 1),
        "simulated_risk_score": round(degraded_score, 1),
        "risk_score_increase": round(degraded_score - baseline_score, 1),
        "affected_raw_materials": affected_materials,
        "affected_shipments": affected_shipments,
        "recommendation": (
            f"If '{supplier.name}' fails at {severity * 100:.0f}% severity, its risk score would rise from "
            f"{baseline_score:.0f}% to {degraded_score:.0f}%, impacting {affected_materials} raw material line(s) "
            f"and {affected_shipments} shipment(s). Identify backup suppliers in the same category now."
        ),
    }


def simulate_demand_spike(db: Session, params: dict) -> dict:
    material = _require_material(db, int(params["raw_material_id"]))
    spike_pct = float(params.get("spike_percentage", 30))
    daily_consumption = float(params.get("current_daily_consumption", max(material.reorder_level / 14, 1)))

    new_daily_consumption = daily_consumption * (1 + spike_pct / 100)
    days_until_stockout_baseline = material.quantity_on_hand / daily_consumption if daily_consumption else float("inf")
    days_until_stockout_spike = material.quantity_on_hand / new_daily_consumption if new_daily_consumption else float("inf")

    shortfall_units = max(0.0, (new_daily_consumption * material.lead_time_days) - material.quantity_on_hand)

    return {
        "raw_material_id": material.id,
        "raw_material_name": material.name,
        "spike_percentage": spike_pct,
        "baseline_daily_consumption": round(daily_consumption, 2),
        "simulated_daily_consumption": round(new_daily_consumption, 2),
        "days_until_stockout_baseline": round(days_until_stockout_baseline, 1),
        "days_until_stockout_simulated": round(days_until_stockout_spike, 1),
        "recommended_emergency_order_quantity": round(shortfall_units, 1),
        "recommendation": (
            f"A {spike_pct:.0f}% demand spike shortens the stockout horizon for '{material.name}' from "
            f"{days_until_stockout_baseline:.1f} to {days_until_stockout_spike:.1f} days. Place an emergency order "
            f"of approximately {shortfall_units:.0f} {material.unit} to cover the supplier's "
            f"{material.lead_time_days}-day lead time."
            if shortfall_units > 0
            else f"A {spike_pct:.0f}% demand spike still leaves enough buffer stock for '{material.name}' to cover "
            f"the {material.lead_time_days}-day lead time."
        ),
    }


def simulate_lead_time_increase(db: Session, params: dict) -> dict:
    supplier = _require_supplier(db, int(params["supplier_id"]))
    added_days = float(params.get("added_days", 7))
    quantity = float(params.get("order_quantity", 500))

    order_date = date.today()
    baseline_expected = order_date + timedelta(days=int(supplier.avg_lead_time_days))
    simulated_expected = order_date + timedelta(days=int(supplier.avg_lead_time_days + added_days))

    baseline_features = build_delay_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, quantity, order_date, baseline_expected, supplier.order_volume_last_year,
    )
    simulated_features = build_delay_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days + added_days, quantity, order_date, simulated_expected, supplier.order_volume_last_year,
    )

    baseline_days, baseline_prob = ai_predict.score_delay_features(baseline_features)
    simulated_days, simulated_prob = ai_predict.score_delay_features(simulated_features)

    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "added_lead_time_days": added_days,
        "baseline_predicted_delay_days": round(baseline_days, 2),
        "simulated_predicted_delay_days": round(simulated_days, 2),
        "baseline_delay_probability": round(baseline_prob, 3),
        "simulated_delay_probability": round(simulated_prob, 3),
        "production_impact": estimate_production_impact(simulated_days, quantity),
        "recommendation": (
            f"Extending '{supplier.name}'s lead time by {added_days:.0f} days raises delay probability from "
            f"{baseline_prob * 100:.0f}% to {simulated_prob * 100:.0f}% and predicted delay from "
            f"{baseline_days:.1f} to {simulated_days:.1f} days."
        ),
    }


def simulate_raw_material_shortage(db: Session, params: dict) -> dict:
    material = _require_material(db, int(params["raw_material_id"]))
    shortage_pct = float(params.get("shortage_percentage", 40))
    quantity = float(params.get("order_quantity", 500))

    shortfall_days = (material.lead_time_days * shortage_pct / 100) / 2
    simulated_delay_days = max(0.0, shortfall_days)
    impact = estimate_production_impact(simulated_delay_days, quantity)

    return {
        "raw_material_id": material.id,
        "raw_material_name": material.name,
        "shortage_percentage": shortage_pct,
        "estimated_additional_delay_days": round(simulated_delay_days, 2),
        "production_impact": impact,
        "recommendation": (
            f"A {shortage_pct:.0f}% shortage of '{material.name}' is estimated to add roughly "
            f"{simulated_delay_days:.1f} days of delay, with the cost/severity shown in the production impact analysis."
        ),
    }


DISPATCH = {
    ScenarioType.SUPPLIER_FAILURE: simulate_supplier_failure,
    ScenarioType.DEMAND_SPIKE: simulate_demand_spike,
    ScenarioType.LEAD_TIME_INCREASE: simulate_lead_time_increase,
    ScenarioType.RAW_MATERIAL_SHORTAGE: simulate_raw_material_shortage,
}


def run_scenario(db: Session, scenario_type: ScenarioType, params: dict) -> dict:
    handler = DISPATCH.get(scenario_type)
    if handler is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown scenario type.")
    return handler(db, params)
