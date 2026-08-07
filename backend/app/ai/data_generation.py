"""
Synthetic data generator for training the AI Risk Prediction Engine (module 6).

Real historical data from Sri Lankan apparel exporters (MAS Holdings, Brandix, Hirdaramani)
is confidential and unavailable to a student project -- this is explicitly acknowledged as
a data limitation in the proposal (section 11.1). Instead we generate a realistic synthetic
dataset with Faker + numpy: supplier performance metrics are sampled from distributions that
mirror the industry figures cited in the proposal's literature review, and shipment outcomes
(delay days, anomalies) are produced by a documented ground-truth generative process plus
Gaussian/Bernoulli noise, so the ML models have genuine, learnable signal instead of a
formula they can memorize perfectly.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from app.ai.features import (
    build_anomaly_features,
    build_delay_features,
    build_demand_features,
    build_risk_features,
    build_stockout_features,
)

SEED = 42


@dataclass
class SyntheticSupplier:
    name: str
    country: str
    category: str
    on_time_delivery_rate: float
    defect_rate: float
    cancellation_rate: float
    avg_lead_time_days: float
    order_volume_last_year: int
    true_risk: float  # latent ground-truth risk propensity in [0, 1], used only to label training data


CATEGORIES = ["fabric", "buttons", "zippers", "thread", "packaging", "trims", "dye_chemicals"]
COUNTRIES = ["Sri Lanka", "India", "China", "Bangladesh", "Vietnam", "Indonesia", "Pakistan"]


def generate_suppliers(n: int = 650, seed: int = SEED) -> list[SyntheticSupplier]:
    fake = Faker()
    Faker.seed(seed)
    rng = np.random.default_rng(seed)
    random.seed(seed)

    suppliers = []
    for _ in range(n):
        # Latent, unobserved "true risk" drives all the observable metrics below,
        # so the metrics are correlated the way real supplier risk factors would be.
        true_risk = float(np.clip(rng.beta(2, 5), 0, 1))

        on_time = float(np.clip(rng.normal(0.97 - 0.35 * true_risk, 0.05), 0.35, 0.999))
        defect = float(np.clip(rng.normal(0.01 + 0.10 * true_risk, 0.015), 0.0, 0.4))
        cancel = float(np.clip(rng.normal(0.01 + 0.09 * true_risk, 0.015), 0.0, 0.35))
        lead_time = float(np.clip(rng.normal(10 + 25 * true_risk, 4), 3, 75))
        volume = int(np.clip(rng.normal(120 - 60 * true_risk, 40), 5, 400))

        suppliers.append(
            SyntheticSupplier(
                name=fake.company(),
                country=random.choice(COUNTRIES),
                category=random.choice(CATEGORIES),
                on_time_delivery_rate=round(on_time, 4),
                defect_rate=round(defect, 4),
                cancellation_rate=round(cancel, 4),
                avg_lead_time_days=round(lead_time, 1),
                order_volume_last_year=volume,
                true_risk=true_risk,
            )
        )
    return suppliers


def suppliers_to_training_frame(suppliers: list[SyntheticSupplier], seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in suppliers:
        features = build_risk_features(
            s.on_time_delivery_rate, s.defect_rate, s.cancellation_rate, s.avg_lead_time_days, s.order_volume_last_year
        )
        # Binary "is_high_risk" label: a threshold on the latent true_risk propensity (as a real
        # analyst would retrospectively flag underperforming suppliers), with a small random label
        # flip to simulate occasional real-world mislabeling -- not a raw Bernoulli draw on the
        # propensity itself, which would make the label irreducibly noisy and cap accuracy near chance.
        is_high_risk = int(s.true_risk > 0.32)
        if rng.random() < 0.06:
            is_high_risk = 1 - is_high_risk
        rows.append({**features, "is_high_risk": is_high_risk, "true_risk": s.true_risk})
    return pd.DataFrame(rows)


def generate_shipments_training_frame(suppliers: list[SyntheticSupplier], n: int = 3600, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    rows = []
    start = date(2023, 1, 1)

    for _ in range(n):
        s = suppliers[rng.integers(0, len(suppliers))]
        order_date = start + timedelta(days=int(rng.integers(0, 900)))
        requested_lead = int(np.clip(rng.normal(s.avg_lead_time_days, 5), 3, 90))
        expected_delivery = order_date + timedelta(days=requested_lead)
        base_quantity = float(np.clip(rng.normal(500 + 300 * (1 - s.true_risk), 250), 20, 5000))

        # Ground truth: expected delay driven by supplier risk, seasonal peak-season strain
        # (Aug-Dec buyer deadlines), and workload pressure (quantity vs. lead time), plus noise.
        seasonal_strain = 1.0 if expected_delivery.month in (8, 9, 10, 11, 12) else 0.3
        workload_pressure = base_quantity / max(requested_lead, 1) / 40.0
        base_delay = (
            18 * s.true_risk
            + 4 * seasonal_strain
            + 3 * min(workload_pressure, 3)
            - 6 * s.on_time_delivery_rate
        )
        delay_days = float(max(0.0, rng.normal(base_delay, 3.5)))
        is_delayed = int(delay_days > 1.5)

        # ~6% of shipments are structural anomalies: a sudden, unexplained spike
        # unrelated to the normal risk drivers (e.g. a one-off customs seizure). The
        # perturbation is applied to the *observed* quantity before any features are
        # built, so training features match exactly what inference would see live.
        is_anomaly = int(rng.random() < 0.06)
        observed_quantity = base_quantity
        if is_anomaly:
            delay_days += float(rng.uniform(20, 45))
            observed_quantity = base_quantity * float(rng.choice([0.15, 3.2]))

        features = build_delay_features(
            s.on_time_delivery_rate,
            s.defect_rate,
            s.cancellation_rate,
            s.avg_lead_time_days,
            observed_quantity,
            order_date,
            expected_delivery,
            s.order_volume_last_year,
        )
        anomaly_features = build_anomaly_features(
            observed_quantity,
            requested_lead,
            s.on_time_delivery_rate,
            s.defect_rate,
            s.cancellation_rate,
            expected_delivery,
        )

        rows.append(
            {
                **features,
                **{f"anom_{k}": v for k, v in anomaly_features.items() if k not in features},
                "quantity": observed_quantity,
                "requested_lead_time_days": requested_lead,
                "delay_days": round(delay_days, 2),
                "is_delayed": is_delayed,
                "is_anomaly": is_anomaly,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class SyntheticMaterial:
    category: str
    unit_cost: float
    lead_time_days: int
    reorder_level: float
    supplier_on_time_rate: float
    true_demand_intensity: float  # latent monthly-consumption propensity in [0, 1]


def generate_materials(n: int = 500, seed: int = SEED) -> list[SyntheticMaterial]:
    rng = np.random.default_rng(seed + 2)
    materials = []
    for _ in range(n):
        true_demand_intensity = float(np.clip(rng.beta(2, 3), 0, 1))
        reorder_level = float(np.clip(rng.normal(80 + 200 * true_demand_intensity, 40), 10, 500))
        materials.append(
            SyntheticMaterial(
                category=random.choice(CATEGORIES),
                unit_cost=float(np.clip(rng.lognormal(mean=1.0, sigma=0.8), 0.3, 60)),
                lead_time_days=int(np.clip(rng.normal(18, 8), 3, 60)),
                reorder_level=round(reorder_level, 1),
                supplier_on_time_rate=float(np.clip(rng.normal(0.85, 0.12), 0.35, 0.99)),
                true_demand_intensity=true_demand_intensity,
            )
        )
    return materials


def generate_material_demand_training_frame(
    materials: list[SyntheticMaterial], n: int = 3500, seed: int = SEED
) -> pd.DataFrame:
    """Ground truth: a material's next-30-day consumption is driven by its latent demand
    intensity and apparel peak-season strain (Aug-Dec), plus noise. The stockout label
    additionally uses a *noisier* draw of that same demand (representing real demand
    volatility a forecast can't fully capture) so the classifier can't trivially derive
    the label from the forecast feature alone."""
    rng = np.random.default_rng(seed + 3)
    start = date(2023, 1, 1)
    rows = []

    for _ in range(n):
        m = materials[rng.integers(0, len(materials))]
        as_of = start + timedelta(days=int(rng.integers(0, 900)))
        seasonal_strain = 1.4 if as_of.month in (8, 9, 10, 11, 12) else 0.9

        base_monthly_demand = (20 + 220 * m.true_demand_intensity) * seasonal_strain
        actual_demand_next_30_days = float(max(0.0, rng.normal(base_monthly_demand, base_monthly_demand * 0.2)))
        # A forecast model never sees the future perfectly -- simulate forecast error
        # independent of the noisier "actual" draw used for the stockout ground truth below.
        forecast_demand = float(max(0.0, rng.normal(base_monthly_demand, base_monthly_demand * 0.15)))
        stockout_actual_demand = float(max(0.0, rng.normal(base_monthly_demand, base_monthly_demand * 0.3)))

        quantity_on_hand = float(np.clip(rng.normal(m.reorder_level * 1.3, m.reorder_level * 0.9), 0, m.reorder_level * 5))

        demand_features = build_demand_features(
            quantity_on_hand, m.reorder_level, m.unit_cost, m.lead_time_days, m.supplier_on_time_rate, as_of
        )

        daily_consumption = stockout_actual_demand / 30.0
        depletion_at_lead_time = quantity_on_hand - daily_consumption * m.lead_time_days
        stockout = int(depletion_at_lead_time < 0)
        if rng.random() < 0.05:  # real-world noise: emergency reorders, demand shocks, etc.
            stockout = 1 - stockout

        stockout_features = build_stockout_features(
            quantity_on_hand, m.reorder_level, m.lead_time_days, m.supplier_on_time_rate, as_of, forecast_demand
        )

        rows.append(
            {
                **demand_features,
                **{f"stk_{k}": v for k, v in stockout_features.items() if k not in demand_features},
                "expected_demand_next_30_days": forecast_demand,
                "actual_demand_next_30_days": round(actual_demand_next_30_days, 2),
                "stockout_within_lead_time": stockout,
            }
        )
    return pd.DataFrame(rows)
