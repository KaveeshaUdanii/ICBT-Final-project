"""
Explainable AI / XAI module (module 8).

The `lime` package could not be installed in this environment (its legacy setup.py is
incompatible with this system's patched distutils), so this module implements the same
methodology described in Ribeiro, Singh & Guestrin (2016) -- the paper the proposal itself
cites for LIME -- directly:

  1. Perturb the instance being explained by sampling nearby points in feature space.
  2. Query the real model (predict_fn) for each perturbed point.
  3. Weight each sample by its proximity to the original instance (an exponential kernel).
  4. Fit an interpretable weighted linear (Ridge) surrogate model on these local samples.
  5. Read the surrogate's coefficients as each feature's local contribution.

This is "Local Interpretable Model-Agnostic Explanations" applied to tabular data,
implemented from first principles instead of via the third-party package.
"""

import json
from functools import lru_cache
from typing import Callable

import numpy as np
from sklearn.linear_model import Ridge

from app.ai.features import FEATURE_LABELS
from app.core.config import settings

MODELS_DIR = settings.ML_MODELS_DIR

# Features that are naturally a 0-1 fraction -- rendered as a percentage rather than a raw
# decimal (e.g. "60%" instead of "0.60"), which reads as a business metric instead of a
# model-internal value.
_PERCENT_FEATURES = {
    "on_time_delivery_rate",
    "defect_rate",
    "cancellation_rate",
    "supplier_on_time_rate",
    "supplier_defect_rate",
    "supplier_cancellation_rate",
}


def _format_value(feature: str, value: float) -> str:
    if feature in _PERCENT_FEATURES:
        return f"{value * 100:.0f}%"
    if feature.endswith("_days"):
        return f"{value:.0f} days"
    if abs(value - round(value)) < 1e-9:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


@lru_cache(maxsize=1)
def _load_feature_stats() -> dict:
    path = MODELS_DIR / "feature_stats.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def clear_stats_cache() -> None:
    _load_feature_stats.cache_clear()


def explain_instance(
    model_name: str,
    stats_key: str,
    instance: dict,
    feature_order: list[str],
    predict_fn: Callable[[np.ndarray], np.ndarray],
    num_samples: int = 800,
    top_k: int = 5,
    seed: int = 0,
    higher_is_worse: bool = True,
) -> dict:
    stats = _load_feature_stats().get(stats_key, {})
    means = np.array([stats.get(f, {}).get("mean", instance[f]) for f in feature_order])
    stds = np.array([max(stats.get(f, {}).get("std", 1.0), 1e-6) for f in feature_order])
    mins = np.array([stats.get(f, {}).get("min", instance[f] - 3 * s) for f, s in zip(feature_order, stds)])
    maxs = np.array([stats.get(f, {}).get("max", instance[f] + 3 * s) for f, s in zip(feature_order, stds)])

    x_vec = np.array([float(instance[f]) for f in feature_order])

    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, size=(num_samples, len(feature_order)))
    # A tighter neighborhood (0.35 std) keeps the surrogate local and faithful; combined with
    # stronger Ridge regularization below, this curbs the coefficient-sign instability that
    # correlated tabular features (e.g. on-time rate vs. cancellation rate) otherwise cause.
    samples = x_vec + noise * stds * 0.35
    samples = np.clip(samples, mins, maxs)
    samples[0] = x_vec  # ensure the exact instance is included in the local neighborhood

    predictions = predict_fn(samples)

    # Proximity weighting: an exponential (RBF) kernel over normalized distance, exactly as
    # LIME's reference implementation weights its local samples.
    normalized_dist = np.linalg.norm((samples - x_vec) / stds, axis=1)
    kernel_width = np.sqrt(len(feature_order)) * 0.75
    weights = np.exp(-(normalized_dist**2) / (kernel_width**2))

    samples_std = (samples - means) / stds
    surrogate = Ridge(alpha=5.0)
    surrogate.fit(samples_std, predictions, sample_weight=weights)

    x_std = (x_vec - means) / stds
    contributions = surrogate.coef_ * x_std

    order = np.argsort(-np.abs(contributions))[:top_k]

    factors = []
    for idx in order:
        f = feature_order[idx]
        val = float(x_vec[idx])
        mean_val = float(means[idx])
        contribution = float(contributions[idx])
        raises = contribution > 0 if higher_is_worse else contribution < 0
        direction = "increases_risk" if raises else "decreases_risk"
        label = FEATURE_LABELS.get(f, f)
        display_value = _format_value(f, val)
        typical_display_value = _format_value(f, mean_val)
        # Short and data-forward rather than a full repeated sentence per factor (direction
        # and relative magnitude are already carried by the row's icon/color and bar in the
        # UI, so the text only needs to add the one thing they can't: this case's actual
        # number against what's typical for this model). Reports the model's local
        # attribution for *this* case rather than asserting a general "higher/lower than
        # typical always does X" rule -- the underlying models (Random Forest, XGBoost,
        # Isolation Forest) can be non-monotonic, so a feature's effect near this instance
        # does not have to match its global correlation direction.
        explanation = f"{display_value} recorded, vs. a typical {typical_display_value} for this model."
        factors.append(
            {
                "feature": f,
                "label": label,
                "value": val,
                "display_value": display_value,
                "typical_display_value": typical_display_value,
                "contribution": round(contribution, 4),
                "direction": direction,
                "explanation": explanation,
            }
        )

    prediction_value = float(predict_fn(x_vec.reshape(1, -1))[0])
    base_value = float(np.average(predictions, weights=weights))

    top_names = [FEATURE_LABELS.get(feature_order[i], feature_order[i]) for i in order[:3]]
    if len(top_names) >= 2:
        summary = (
            f"This prediction is mainly driven by {', '.join(top_names[:-1])} and {top_names[-1]}."
        )
    elif top_names:
        summary = f"This prediction is mainly driven by {top_names[0]}."
    else:
        summary = "No dominant factor was identified."

    return {
        "model_name": model_name,
        "base_value": round(base_value, 4),
        "prediction": round(prediction_value, 4),
        "top_factors": factors,
        "plain_language_summary": summary,
    }
