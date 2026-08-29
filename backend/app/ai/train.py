"""
Trains the five models of the AI Risk Prediction Engine (module 6) and persists them (plus a
performance report) to app/ml_models/. Run directly:

    python -m app.ai.train

Training data comes from ml_pipeline/data/processed/*.csv -- the cleaned, feature-engineered
output of the preprocessing/EDA notebooks in ml_pipeline/notebooks/ (themselves cleaning the
large, deliberately messy source records in ml_pipeline/data/raw/). This guarantees the model
serving live predictions is provably trained on the exact same cleaned dataset the notebooks
document and analyze, not a second, independently-generated copy.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from app.ai.features import FEATURES_ANOMALY, FEATURES_DELAY, FEATURES_DEMAND, FEATURES_RISK, FEATURES_STOCKOUT
from app.core.config import settings

MODELS_DIR = settings.ML_MODELS_DIR
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BACKEND_DIR / "ml_pipeline" / "data" / "processed"


def _load_processed(filename: str) -> pd.DataFrame:
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m ml_pipeline.build_source_datasets` and execute the "
            f"notebooks in ml_pipeline/notebooks/ first (or restore the committed processed CSVs)."
        )
    return pd.read_csv(path)


def _clf_metrics(y_true, y_pred, y_proba=None) -> dict:
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
    }
    if y_proba is not None and len(set(y_true)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
    return metrics


def _save_feature_stats(existing: dict, key: str, df, features: list[str]) -> dict:
    existing[key] = {
        f: {
            "mean": round(float(df[f].mean()), 6),
            "std": round(float(df[f].std() or 1e-6), 6),
            "min": round(float(df[f].min()), 6),
            "max": round(float(df[f].max()), 6),
        }
        for f in features
    }
    return existing


def train_supplier_risk_models(report: dict, feature_stats: dict) -> None:
    df = _load_processed("supplier_performance_cleaned.csv")
    _save_feature_stats(feature_stats, "risk", df, FEATURES_RISK)
    X = df[FEATURES_RISK].values
    y = df["is_high_risk"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    logreg = LogisticRegression(max_iter=1000, class_weight="balanced")
    logreg.fit(X_train_s, y_train)

    rf = RandomForestClassifier(n_estimators=300, max_depth=6, class_weight="balanced", random_state=42)
    rf.fit(X_train, y_train)

    # Ensemble score = average of both models' probability of "high risk", scaled to 0-100.
    logreg_proba = logreg.predict_proba(X_test_s)[:, 1]
    rf_proba = rf.predict_proba(X_test)[:, 1]
    ensemble_proba = (logreg_proba + rf_proba) / 2
    ensemble_pred = (ensemble_proba >= 0.5).astype(int)

    joblib.dump(scaler, MODELS_DIR / "risk_scaler.joblib")
    joblib.dump(logreg, MODELS_DIR / "risk_logreg.joblib")
    joblib.dump(rf, MODELS_DIR / "risk_random_forest.joblib")

    report["supplier_risk_scoring_model"] = {
        "algorithm": "Logistic Regression + Random Forest (ensemble average)",
        "features": FEATURES_RISK,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "logistic_regression": _clf_metrics(y_test, (logreg_proba >= 0.5).astype(int), logreg_proba),
        "random_forest": _clf_metrics(y_test, (rf_proba >= 0.5).astype(int), rf_proba),
        "ensemble": _clf_metrics(y_test, ensemble_pred, ensemble_proba),
        "feature_importance_random_forest": {
            f: round(float(imp), 4) for f, imp in zip(FEATURES_RISK, rf.feature_importances_)
        },
    }


def train_delay_models(report: dict, feature_stats: dict) -> None:
    df = _load_processed("shipment_logistics_cleaned.csv")
    _save_feature_stats(feature_stats, "delay", df, FEATURES_DELAY)

    X = df[FEATURES_DELAY].values
    y_class = df["is_delayed"].values
    y_reg = df["delay_days"].values

    X_train, X_test, yc_train, yc_test, yr_train, yr_test = train_test_split(
        X, y_class, y_reg, test_size=0.25, random_state=42, stratify=y_class
    )

    clf = XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X_train, yc_train)
    clf_proba = clf.predict_proba(X_test)[:, 1]
    clf_pred = (clf_proba >= 0.5).astype(int)

    reg = XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    reg.fit(X_train, yr_train)
    reg_pred = np.clip(reg.predict(X_test), 0, None)
    mae = float(np.mean(np.abs(reg_pred - yr_test)))
    rmse = float(np.sqrt(np.mean((reg_pred - yr_test) ** 2)))

    joblib.dump(clf, MODELS_DIR / "delay_classifier.joblib")
    joblib.dump(reg, MODELS_DIR / "delay_regressor.joblib")

    report["delay_prediction_model"] = {
        "algorithm": "XGBoost (classifier for delay probability + regressor for delay magnitude)",
        "features": FEATURES_DELAY,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "classifier_metrics": _clf_metrics(yc_test, clf_pred, clf_proba),
        "regressor_metrics": {"mae_days": round(mae, 3), "rmse_days": round(rmse, 3)},
        "feature_importance": {f: round(float(imp), 4) for f, imp in zip(FEATURES_DELAY, clf.feature_importances_)},
    }


def train_anomaly_model(report: dict, feature_stats: dict) -> None:
    df = _load_processed("shipment_logistics_cleaned.csv")
    _save_feature_stats(feature_stats, "anomaly", df, FEATURES_ANOMALY)

    X = df[FEATURES_ANOMALY].values
    y_true = df["is_anomaly"].values  # only used to *evaluate* the unsupervised model

    model = IsolationForest(n_estimators=300, contamination=settings.ANOMALY_CONTAMINATION, random_state=42)
    model.fit(X)

    # IsolationForest: -1 = anomaly, 1 = normal. Convert to {1: anomaly, 0: normal} for scoring.
    raw_pred = model.predict(X)
    y_pred = (raw_pred == -1).astype(int)

    joblib.dump(model, MODELS_DIR / "anomaly_isolation_forest.joblib")

    report["anomaly_detection_model"] = {
        "algorithm": "Isolation Forest (unsupervised)",
        "features": FEATURES_ANOMALY,
        "training_samples": int(len(X)),
        "contamination": settings.ANOMALY_CONTAMINATION,
        "evaluation_against_injected_anomalies": _clf_metrics(y_true, y_pred),
        "note": "Metrics are evaluated against synthetically injected anomalies for validation "
        "purposes only; the model itself is trained unsupervised, matching the proposal's design.",
    }


def train_demand_forecast_model(report: dict, feature_stats: dict) -> None:
    """Demand Forecasting Model (module addition #1): predicts a raw material's expected
    consumption over the next 30 days, so warehouse staff can reorder proactively instead
    of only reacting once stock has already crossed the reorder line."""
    df = _load_processed("inventory_demand_cleaned.csv")
    _save_feature_stats(feature_stats, "demand", df, FEATURES_DEMAND)

    X = df[FEATURES_DEMAND].values
    y = df["actual_demand_next_30_days"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    # Hyperparameters tuned via GridSearchCV in ml_pipeline/notebooks/03_..._modeling.ipynb
    # (Section 9g) -- a ~13% MAE reduction over the untuned defaults previously used here,
    # confirmed via the same 5-fold cross-validation the algorithm benchmark itself uses.
    model = GradientBoostingRegressor(
        n_estimators=400, max_depth=5, learning_rate=0.08, subsample=0.9, random_state=42
    )
    model.fit(X_train, y_train)
    pred = np.clip(model.predict(X_test), 0, None)
    mae = float(np.mean(np.abs(pred - y_test)))
    rmse = float(np.sqrt(np.mean((pred - y_test) ** 2)))
    mean_actual = float(np.mean(y_test))

    joblib.dump(model, MODELS_DIR / "demand_forecast_gbr.joblib")

    report["demand_forecasting_model"] = {
        "algorithm": "Gradient Boosting Regressor",
        "features": FEATURES_DEMAND,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "regressor_metrics": {
            "mae_units": round(mae, 2),
            "rmse_units": round(rmse, 2),
            "mean_actual_demand_units": round(mean_actual, 2),
            "mae_as_pct_of_mean": round(100 * mae / mean_actual, 1) if mean_actual else None,
        },
        "feature_importance": {f: round(float(imp), 4) for f, imp in zip(FEATURES_DEMAND, model.feature_importances_)},
        "note": "Additional model beyond the proposal's 3 required models -- predicts next-30-day "
        "material consumption to support proactive procurement (Warehouse Manager dashboard).",
    }


def train_stockout_risk_model(report: dict, feature_stats: dict) -> None:
    """Inventory Stockout Risk Model (module addition #2): classifies whether a material
    will run out before replenishment arrives, given current stock, lead time, supplier
    reliability, and the Demand Forecasting Model's own predicted demand as an input
    feature -- a small two-stage pipeline (forecast -> risk), not two independent models."""
    df = _load_processed("inventory_demand_cleaned.csv")
    _save_feature_stats(feature_stats, "stockout", df, FEATURES_STOCKOUT)

    X = df[FEATURES_STOCKOUT].values
    y = df["stockout_within_lead_time"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = GradientBoostingClassifier(n_estimators=250, max_depth=3, learning_rate=0.07, random_state=42)
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    joblib.dump(model, MODELS_DIR / "stockout_risk_gbc.joblib")

    report["stockout_risk_model"] = {
        "algorithm": "Gradient Boosting Classifier",
        "features": FEATURES_STOCKOUT,
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "classifier_metrics": _clf_metrics(y_test, pred, proba),
        "feature_importance": {f: round(float(imp), 4) for f, imp in zip(FEATURES_STOCKOUT, model.feature_importances_)},
        "note": "Additional model beyond the proposal's 3 required models -- consumes the Demand "
        "Forecasting Model's prediction as one of its own input features (a stacked pipeline).",
    }


def train_chatbot_intent_model(report: dict) -> None:
    """Supplier Portal chatbot (6th model, addition beyond the proposal's required set): a
    local TF-IDF + Logistic Regression intent classifier, trained on a small fixed set of
    example phrasings -- no external API/LLM involved. See app/ai/chatbot.py for the intent
    list and the router that answers each intent from real, scoped backend data."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    from app.ai.chatbot import TRAINING_EXAMPLES

    texts = [t for t, _ in TRAINING_EXAMPLES]
    labels = [label for _, label in TRAINING_EXAMPLES]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)
    X = vectorizer.fit_transform(texts)

    clf = LogisticRegression(max_iter=1000)
    clf.fit(X, labels)
    train_accuracy = float(clf.score(X, labels))

    joblib.dump(vectorizer, MODELS_DIR / "chatbot_vectorizer.joblib")
    joblib.dump(clf, MODELS_DIR / "chatbot_intent_classifier.joblib")

    report["chatbot_intent_model"] = {
        "algorithm": "TF-IDF (1-2 grams) + Logistic Regression",
        "intents": sorted(set(labels)),
        "training_examples": len(texts),
        "training_accuracy": round(train_accuracy, 4),
        "note": "Local, no-external-API chatbot for the Supplier Portal -- classifies intent only; "
        "every answer is generated from the caller's own real, scoped backend data, not the model.",
    }


def main() -> dict:
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "synthetic (Faker + numpy), cleaned via the ml_pipeline/notebooks/ preprocessing "
        "pipeline -- see ml_pipeline/data/processed/*.csv",
    }
    feature_stats: dict = {}

    train_supplier_risk_models(report, feature_stats)
    train_delay_models(report, feature_stats)
    train_anomaly_model(report, feature_stats)
    train_demand_forecast_model(report, feature_stats)
    train_stockout_risk_model(report, feature_stats)
    train_chatbot_intent_model(report)

    with open(MODELS_DIR / "training_report.json", "w") as f:
        json.dump(report, f, indent=2)
    with open(MODELS_DIR / "feature_stats.json", "w") as f:
        json.dump(feature_stats, f, indent=2)

    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
