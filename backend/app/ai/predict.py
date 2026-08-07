"""
Inference layer for the AI Risk Prediction Engine (module 6). Loads the joblib artifacts
produced by app.ai.train and exposes small, pure functions that turn a feature vector into
a prediction. Kept separate from explain.py so the explainer can reuse these exact
prediction functions when perturbing inputs (required for a faithful local explanation).
"""

from functools import lru_cache

import joblib
import numpy as np

from app.ai.features import FEATURES_ANOMALY, FEATURES_DELAY, FEATURES_DEMAND, FEATURES_RISK, FEATURES_STOCKOUT
from app.core.config import settings

MODELS_DIR = settings.ML_MODELS_DIR

REQUIRED_MODEL_FILES = [
    "risk_scaler.joblib",
    "risk_logreg.joblib",
    "risk_random_forest.joblib",
    "delay_classifier.joblib",
    "delay_regressor.joblib",
    "anomaly_isolation_forest.joblib",
    "demand_forecast_gbr.joblib",
    "stockout_risk_gbc.joblib",
]


def models_are_trained() -> bool:
    return all((MODELS_DIR / name).exists() for name in REQUIRED_MODEL_FILES)


@lru_cache(maxsize=1)
def _load_all():
    return {
        "risk_scaler": joblib.load(MODELS_DIR / "risk_scaler.joblib"),
        "risk_logreg": joblib.load(MODELS_DIR / "risk_logreg.joblib"),
        "risk_rf": joblib.load(MODELS_DIR / "risk_random_forest.joblib"),
        "delay_classifier": joblib.load(MODELS_DIR / "delay_classifier.joblib"),
        "delay_regressor": joblib.load(MODELS_DIR / "delay_regressor.joblib"),
        "anomaly_model": joblib.load(MODELS_DIR / "anomaly_isolation_forest.joblib"),
        "demand_forecast_model": joblib.load(MODELS_DIR / "demand_forecast_gbr.joblib"),
        "stockout_risk_model": joblib.load(MODELS_DIR / "stockout_risk_gbc.joblib"),
    }


def clear_model_cache() -> None:
    _load_all.cache_clear()


def risk_predict_proba(X: np.ndarray) -> np.ndarray:
    """Ensemble (LogReg + RandomForest) probability of 'high risk' for a batch of rows."""
    models = _load_all()
    X_scaled = models["risk_scaler"].transform(X)
    logreg_p = models["risk_logreg"].predict_proba(X_scaled)[:, 1]
    rf_p = models["risk_rf"].predict_proba(X)[:, 1]
    return (logreg_p + rf_p) / 2


def delay_predict_proba(X: np.ndarray) -> np.ndarray:
    models = _load_all()
    return models["delay_classifier"].predict_proba(X)[:, 1]


def delay_predict_days(X: np.ndarray) -> np.ndarray:
    models = _load_all()
    return np.clip(models["delay_regressor"].predict(X), 0, None)


def anomaly_predict(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Returns (is_anomaly[0/1], anomaly_score[0-1, higher = more anomalous])."""
    models = _load_all()
    model = models["anomaly_model"]
    raw_pred = model.predict(X)  # -1 anomaly, 1 normal
    is_anomaly = (raw_pred == -1).astype(int)
    # decision_function: higher = more normal. Flip and min-max scale to an intuitive 0-1 score.
    raw_scores = model.decision_function(X)
    scaled = 1 / (1 + np.exp(raw_scores * 4))  # logistic squashing centered at the decision boundary (0)
    return is_anomaly, scaled


def demand_predict(X: np.ndarray) -> np.ndarray:
    models = _load_all()
    return np.clip(models["demand_forecast_model"].predict(X), 0, None)


def stockout_predict_proba(X: np.ndarray) -> np.ndarray:
    models = _load_all()
    return models["stockout_risk_model"].predict_proba(X)[:, 1]


def score_supplier_features(feature_dict: dict) -> float:
    """Convenience: returns a single risk score (0-100) for one supplier's features."""
    X = np.array([[feature_dict[f] for f in FEATURES_RISK]])
    return float(risk_predict_proba(X)[0] * 100)


def score_delay_features(feature_dict: dict) -> tuple[float, float]:
    X = np.array([[feature_dict[f] for f in FEATURES_DELAY]])
    return float(delay_predict_days(X)[0]), float(delay_predict_proba(X)[0])


def score_anomaly_features(feature_dict: dict) -> tuple[bool, float]:
    X = np.array([[feature_dict[f] for f in FEATURES_ANOMALY]])
    is_anom, score = anomaly_predict(X)
    return bool(is_anom[0]), float(score[0])


def score_demand_features(feature_dict: dict) -> float:
    X = np.array([[feature_dict[f] for f in FEATURES_DEMAND]])
    return float(demand_predict(X)[0])


def score_stockout_features(feature_dict: dict) -> float:
    X = np.array([[feature_dict[f] for f in FEATURES_STOCKOUT]])
    return float(stockout_predict_proba(X)[0])
