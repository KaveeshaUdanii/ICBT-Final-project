"""
Shared feature engineering used identically at training time (on synthetic historical
data) and at inference time (on live Supplier/Shipment records), so the model never sees
a distribution shift between how it was trained and how it is queried in production.
"""

import math
from datetime import date

FEATURES_RISK = [
    "on_time_delivery_rate",
    "defect_rate",
    "cancellation_rate",
    "avg_lead_time_days",
    "order_volume_last_year",
]

FEATURES_DELAY = [
    "supplier_on_time_rate",
    "supplier_defect_rate",
    "supplier_cancellation_rate",
    "supplier_avg_lead_time_days",
    "order_quantity",
    "quantity_per_lead_time",
    "month_sin",
    "month_cos",
    "requested_lead_time_days",
    "supplier_order_volume_last_year",
]

FEATURES_ANOMALY = [
    "quantity",
    "requested_lead_time_days",
    "supplier_on_time_rate",
    "supplier_defect_rate",
    "supplier_cancellation_rate",
    "month_sin",
    "month_cos",
]

FEATURES_DEMAND = [
    "quantity_on_hand",
    "reorder_level",
    "unit_cost",
    "lead_time_days",
    "supplier_on_time_rate",
    "month_sin",
    "month_cos",
    "quantity_to_reorder_ratio",
]

# Includes "expected_demand_next_30_days" -- at inference time this slot is filled with the
# Demand Forecasting Model's own prediction (a stacked/two-stage pipeline: forecast demand,
# then feed that forecast into the stockout classifier), not a second independent estimate.
FEATURES_STOCKOUT = [
    "quantity_on_hand",
    "reorder_level",
    "lead_time_days",
    "supplier_on_time_rate",
    "month_sin",
    "month_cos",
    "quantity_to_reorder_ratio",
    "expected_demand_next_30_days",
]


def month_cyclic(month: int) -> tuple[float, float]:
    angle = 2 * math.pi * (month / 12.0)
    return math.sin(angle), math.cos(angle)


def build_risk_features(
    on_time_delivery_rate: float,
    defect_rate: float,
    cancellation_rate: float,
    avg_lead_time_days: float,
    order_volume_last_year: int,
) -> dict:
    return {
        "on_time_delivery_rate": on_time_delivery_rate,
        "defect_rate": defect_rate,
        "cancellation_rate": cancellation_rate,
        "avg_lead_time_days": avg_lead_time_days,
        "order_volume_last_year": order_volume_last_year,
    }


def build_delay_features(
    supplier_on_time_rate: float,
    supplier_defect_rate: float,
    supplier_cancellation_rate: float,
    supplier_avg_lead_time_days: float,
    order_quantity: float,
    order_date: date,
    expected_delivery_date: date,
    supplier_order_volume_last_year: int,
) -> dict:
    requested_lead_time_days = max((expected_delivery_date - order_date).days, 1)
    sin_m, cos_m = month_cyclic(expected_delivery_date.month)
    return {
        "supplier_on_time_rate": supplier_on_time_rate,
        "supplier_defect_rate": supplier_defect_rate,
        "supplier_cancellation_rate": supplier_cancellation_rate,
        "supplier_avg_lead_time_days": supplier_avg_lead_time_days,
        "order_quantity": order_quantity,
        "quantity_per_lead_time": order_quantity / requested_lead_time_days,
        "month_sin": sin_m,
        "month_cos": cos_m,
        "requested_lead_time_days": requested_lead_time_days,
        "supplier_order_volume_last_year": supplier_order_volume_last_year,
    }


def build_anomaly_features(
    quantity: float,
    requested_lead_time_days: float,
    supplier_on_time_rate: float,
    supplier_defect_rate: float,
    supplier_cancellation_rate: float,
    expected_delivery_date: date,
) -> dict:
    sin_m, cos_m = month_cyclic(expected_delivery_date.month)
    return {
        "quantity": quantity,
        "requested_lead_time_days": requested_lead_time_days,
        "supplier_on_time_rate": supplier_on_time_rate,
        "supplier_defect_rate": supplier_defect_rate,
        "supplier_cancellation_rate": supplier_cancellation_rate,
        "month_sin": sin_m,
        "month_cos": cos_m,
    }


def build_demand_features(
    quantity_on_hand: float,
    reorder_level: float,
    unit_cost: float,
    lead_time_days: float,
    supplier_on_time_rate: float,
    as_of_date: date,
) -> dict:
    sin_m, cos_m = month_cyclic(as_of_date.month)
    return {
        "quantity_on_hand": quantity_on_hand,
        "reorder_level": reorder_level,
        "unit_cost": unit_cost,
        "lead_time_days": lead_time_days,
        "supplier_on_time_rate": supplier_on_time_rate,
        "month_sin": sin_m,
        "month_cos": cos_m,
        "quantity_to_reorder_ratio": quantity_on_hand / max(reorder_level, 0.01),
    }


def build_stockout_features(
    quantity_on_hand: float,
    reorder_level: float,
    lead_time_days: float,
    supplier_on_time_rate: float,
    as_of_date: date,
    expected_demand_next_30_days: float,
) -> dict:
    sin_m, cos_m = month_cyclic(as_of_date.month)
    return {
        "quantity_on_hand": quantity_on_hand,
        "reorder_level": reorder_level,
        "lead_time_days": lead_time_days,
        "supplier_on_time_rate": supplier_on_time_rate,
        "month_sin": sin_m,
        "month_cos": cos_m,
        "quantity_to_reorder_ratio": quantity_on_hand / max(reorder_level, 0.01),
        "expected_demand_next_30_days": expected_demand_next_30_days,
    }


FEATURE_LABELS = {
    "on_time_delivery_rate": "Supplier on-time delivery rate",
    "defect_rate": "Supplier defect rate",
    "cancellation_rate": "Supplier cancellation rate",
    "avg_lead_time_days": "Supplier average lead time (days)",
    "order_volume_last_year": "Supplier order volume (last year)",
    "supplier_on_time_rate": "Supplier on-time delivery rate",
    "supplier_defect_rate": "Supplier defect rate",
    "supplier_cancellation_rate": "Supplier cancellation rate",
    "supplier_avg_lead_time_days": "Supplier average lead time (days)",
    "order_quantity": "Order quantity",
    "quantity_per_lead_time": "Quantity per lead-time day",
    "month_sin": "Seasonality (sin component)",
    "month_cos": "Seasonality (cos component)",
    "requested_lead_time_days": "Requested lead time (days)",
    "supplier_order_volume_last_year": "Supplier order volume (last year)",
    "quantity": "Shipment quantity",
    "quantity_on_hand": "Current stock on hand",
    "reorder_level": "Reorder level threshold",
    "unit_cost": "Unit cost",
    "lead_time_days": "Supplier lead time (days)",
    "quantity_to_reorder_ratio": "Stock as a multiple of reorder level",
    "expected_demand_next_30_days": "Forecast demand (next 30 days)",
}
