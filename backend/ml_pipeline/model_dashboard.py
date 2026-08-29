"""
Interactive model-interpretability dashboard -- a standalone, lightweight Python view of the
same AI Risk Prediction Engine models the live app serves, built to satisfy a specific gap in the
notebooks: their LIME waterfalls are interactive on hover but fixed to one pre-picked example
per model. This dashboard makes that live -- pick any real supplier, shipment, or material from
the seeded database and see its own waterfall and the model's benchmark context on demand.

Run from the `backend/ml_pipeline/` directory:

    streamlit run model_dashboard.py

Reuses the live app's own trained models, feature builders, and from-scratch LIME implementation
(`app.ai.predict`, `app.ai.features`, `app.ai.explain`) directly, so what this dashboard shows is
provably the same model logic the FastAPI app runs, not a separate copy.
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.ai import predict as ai_predict  # noqa: E402
from app.ai.explain import explain_instance  # noqa: E402
from app.ai.features import (  # noqa: E402
    FEATURES_DELAY,
    FEATURES_RISK,
    FEATURES_STOCKOUT,
    build_delay_features,
    build_risk_features,
    build_stockout_features,
    month_cyclic,
)
from app.core.database import SessionLocal  # noqa: E402
from app.models.raw_material import RawMaterial  # noqa: E402
from app.models.shipment import Shipment  # noqa: E402
from app.models.supplier import Supplier  # noqa: E402

st.set_page_config(page_title="Model Interpretability Dashboard", layout="wide")

# Benchmark results computed once in the accompanying notebooks (Sections 9c/9d, 5-fold
# cross-validation) -- shown here as reference context alongside a live prediction, not
# recomputed on every dashboard load (that would mean refitting several algorithms on tens of
# thousands of rows on every page view, which is neither fast nor the point of this view).
BENCHMARKS = {
    "Supplier Risk": {
        "notebook": "01_suppliers_preprocessing_eda_modeling.ipynb, Section 9c",
        "metric": "F1 (5-fold CV)",
        "rows": [
            ("Baseline: LogReg + RF Ensemble", 0.7629, "winner"),
            ("Random Forest", 0.7457, ""),
            ("CatBoost", 0.7379, ""),
            ("XGBoost", 0.7275, ""),
            ("LightGBM", 0.7049, ""),
        ],
    },
    "Delay Prediction": {
        "notebook": "02_shipments_preprocessing_eda_modeling.ipynb, Section 9c",
        "metric": "F1 (5-fold CV)",
        "rows": [
            ("CatBoost", 0.9060, ""),
            ("LightGBM", 0.9060, ""),
            ("Baseline: XGBoost", 0.9058, "winner (statistically tied, see 9f)"),
            ("Random Forest", 0.9024, ""),
        ],
    },
    "Stockout Risk": {
        "notebook": "03_materials_demand_preprocessing_eda_modeling.ipynb, Section 9d",
        "metric": "F1 (5-fold CV)",
        "rows": [
            ("LightGBM", 0.7714, "0.73pp above baseline -- under the 1-point bar, see notebook"),
            ("XGBoost", 0.7702, ""),
            ("CatBoost", 0.7686, ""),
            ("Baseline: Gradient Boosting", 0.7641, "kept -- gap not meaningful, see 9h"),
            ("Random Forest", 0.7359, ""),
        ],
    },
}


@st.cache_resource
def get_session():
    return SessionLocal()


def render_waterfall(explanation: dict, title: str, y_axis_title: str) -> go.Figure:
    factors = list(reversed(explanation["top_factors"]))
    labels = [f["label"] for f in factors]
    contributions = [f["contribution"] for f in factors]
    hover = [
        f"{f['label']}<br>This record: {f['display_value']}<br>Typical: {f['typical_display_value']}<br>Push: {f['contribution']:+.4f}"
        for f in factors
    ]
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute"] + ["relative"] * len(factors) + ["total"],
            x=["Base (typical)"] + labels + ["Prediction"],
            y=[explanation["base_value"]] + contributions + [0],
            text=[f"{explanation['base_value']:.3f}"] + [f"{c:+.3f}" for c in contributions] + [f"{explanation['prediction']:.3f}"],
            textposition="outside",
            hovertext=["Typical (mean) value across the training population"] + hover + ["Final prediction"],
            hoverinfo="text",
            connector={"line": {"color": "rgba(100,100,100,0.4)"}},
            increasing={"marker": {"color": "#d03b3b"}},
            decreasing={"marker": {"color": "#2a9d5c"}},
            totals={"marker": {"color": "#2a78d6"}},
        )
    )
    fig.update_layout(title=title, yaxis_title=y_axis_title, showlegend=False, height=480)
    return fig


def render_benchmark_table(model_name: str) -> None:
    bench = BENCHMARKS[model_name]
    st.caption(f"Benchmark results from `ml_pipeline/notebooks/{bench['notebook']}` — {bench['metric']}")
    st.table(
        {
            "Algorithm": [r[0] for r in bench["rows"]],
            bench["metric"]: [f"{r[1]:.4f}" for r in bench["rows"]],
            "Note": [r[2] for r in bench["rows"]],
        }
    )


st.title("Model Interpretability Dashboard")
st.write(
    "Pick a real record from the seeded database below to see the AI Risk Prediction Engine's "
    "live prediction for it, explained with the same from-scratch LIME implementation the "
    "FastAPI app uses (`app/ai/explain.py`), alongside the algorithm benchmark each model was "
    "checked against in the accompanying notebook."
)

model_choice = st.sidebar.radio("Model", ["Supplier Risk", "Delay Prediction", "Stockout Risk"])
db = get_session()

if not ai_predict.models_are_trained():
    st.error("Trained model artifacts were not found. Run `python -m app.ai.train` from `backend/` first.")
    st.stop()

if model_choice == "Supplier Risk":
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    if not suppliers:
        st.warning("No suppliers in the database. Run `python seed.py` from `backend/` first.")
        st.stop()
    labels = [f"{s.name} ({s.country}, {s.category})" for s in suppliers]
    idx = st.selectbox("Supplier", range(len(suppliers)), format_func=lambda i: labels[i])
    supplier = suppliers[idx]

    features = build_risk_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, supplier.order_volume_last_year,
    )
    score = ai_predict.score_supplier_features(features) / 100.0

    explanation = explain_instance(
        model_name="Supplier Risk Score",
        stats_key="risk",
        instance=features,
        feature_order=FEATURES_RISK,
        predict_fn=lambda X: ai_predict.risk_predict_proba(np.atleast_2d(X)),
        higher_is_worse=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(
            render_waterfall(explanation, f"LIME Waterfall — {supplier.name}", "Predicted probability of high risk"),
            width="stretch",
        )
    with col2:
        st.metric("Predicted risk score", f"{score * 100:.1f}%")
        st.write(explanation["plain_language_summary"])
    render_benchmark_table("Supplier Risk")

elif model_choice == "Delay Prediction":
    shipments = (
        db.query(Shipment)
        .join(Supplier, Shipment.supplier_id == Supplier.id)
        .order_by(Shipment.expected_delivery_date.desc())
        .limit(100)
        .all()
    )
    if not shipments:
        st.warning("No shipments in the database. Run `python seed.py` from `backend/` first.")
        st.stop()
    labels = [f"{s.shipment_code} — {s.supplier.name} (due {s.expected_delivery_date})" for s in shipments]
    idx = st.selectbox("Shipment (most recent 100)", range(len(shipments)), format_func=lambda i: labels[i])
    shipment = shipments[idx]
    supplier = shipment.supplier

    features = build_delay_features(
        supplier.on_time_delivery_rate, supplier.defect_rate, supplier.cancellation_rate,
        supplier.avg_lead_time_days, shipment.quantity, shipment.order_date,
        shipment.expected_delivery_date, supplier.order_volume_last_year,
    )
    delay_days, delay_prob = ai_predict.score_delay_features(features)

    explanation = explain_instance(
        model_name="Delay Prediction",
        stats_key="delay",
        instance=features,
        feature_order=FEATURES_DELAY,
        predict_fn=lambda X: ai_predict.delay_predict_proba(np.atleast_2d(X)),
        higher_is_worse=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(
            render_waterfall(explanation, f"LIME Waterfall — {shipment.shipment_code}", "Predicted probability of delay"),
            width="stretch",
        )
    with col2:
        st.metric("Predicted delay probability", f"{delay_prob * 100:.1f}%")
        st.metric("Predicted delay magnitude", f"{delay_days:.1f} days")
        st.write(explanation["plain_language_summary"])
    render_benchmark_table("Delay Prediction")

else:  # Stockout Risk
    materials = db.query(RawMaterial).order_by(RawMaterial.name).all()
    if not materials:
        st.warning("No raw materials in the database. Run `python seed.py` from `backend/` first.")
        st.stop()
    labels = [f"{m.name} ({m.category.value})" for m in materials]
    idx = st.selectbox("Raw material", range(len(materials)), format_func=lambda i: labels[i])
    material = materials[idx]
    supplier = material.supplier

    sin_m, cos_m = month_cyclic(date.today().month)
    demand_prediction = ai_predict.demand_predict(
        np.atleast_2d([
            material.quantity_on_hand, material.reorder_level, material.unit_cost, material.lead_time_days,
            supplier.on_time_delivery_rate, sin_m, cos_m,
            material.quantity_on_hand / max(material.reorder_level, 0.01),
        ])
    )[0]
    features = build_stockout_features(
        material.quantity_on_hand, material.reorder_level, material.lead_time_days,
        supplier.on_time_delivery_rate, date.today(), float(demand_prediction),
    )
    stockout_prob = ai_predict.score_stockout_features(features)

    explanation = explain_instance(
        model_name="Stockout Risk",
        stats_key="stockout",
        instance=features,
        feature_order=FEATURES_STOCKOUT,
        predict_fn=lambda X: ai_predict.stockout_predict_proba(np.atleast_2d(X)),
        higher_is_worse=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(
            render_waterfall(explanation, f"LIME Waterfall — {material.name}", "Predicted probability of stockout"),
            width="stretch",
        )
    with col2:
        st.metric("Predicted stockout probability", f"{stockout_prob * 100:.1f}%")
        st.metric("Forecasted 30-day demand", f"{demand_prediction:.1f} {material.unit}")
        st.write(explanation["plain_language_summary"])
    render_benchmark_table("Stockout Risk")
