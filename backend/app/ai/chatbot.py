"""
Local, no-external-API Supplier Portal chatbot (6th AI model).

Trained the same way as every other model in this system -- TF-IDF + Logistic Regression via
scikit-learn, joblib-persisted -- rather than calling a hosted LLM (GPT or otherwise): fully
local, fully explainable (an intent classifier's decision is just which n-grams scored highest
for which class, not an opaque generation process), and consistent with the project's
data-driven, locally-trained approach to every other AI feature.

Scope is deliberately small and honest: a fixed set of intents a Supplier-portal user would
actually need (shipment status, PO status, pending actions, their own performance, help), each
answered by querying the real backend scoped to the caller's own linked supplier -- never a
fabricated or generic response. Anything outside that set is told plainly that it's outside
scope, rather than guessed at.
"""

from __future__ import annotations

import re
from functools import lru_cache

import joblib

from app.core.config import settings

MODELS_DIR = settings.ML_MODELS_DIR

INTENTS = ["greeting", "shipment_status", "po_status", "pending_pos", "performance", "help", "thanks"]

TRAINING_EXAMPLES: list[tuple[str, str]] = [
    # greeting
    ("hi", "greeting"),
    ("hello", "greeting"),
    ("hey there", "greeting"),
    ("good morning", "greeting"),
    ("good afternoon", "greeting"),
    ("hey", "greeting"),
    # shipment_status
    ("where is my shipment", "shipment_status"),
    ("what is the status of my shipment", "shipment_status"),
    ("has my shipment been delivered", "shipment_status"),
    ("track shipment SHP-001-02", "shipment_status"),
    ("status of shipment SHP-018-01", "shipment_status"),
    ("when will my shipment arrive", "shipment_status"),
    ("is my shipment on the way", "shipment_status"),
    ("show me my recent shipments", "shipment_status"),
    ("what shipments do I have pending", "shipment_status"),
    ("check shipment status", "shipment_status"),
    ("is SHP-005-02 delivered yet", "shipment_status"),
    # po_status
    ("what is the status of my purchase order", "po_status"),
    ("status of PO-001-01", "po_status"),
    ("has PO-018-02 been approved", "po_status"),
    ("show me my purchase orders", "po_status"),
    ("is my PO approved yet", "po_status"),
    ("what purchase orders do I have", "po_status"),
    ("check order PO-005-01", "po_status"),
    ("has my order been rejected", "po_status"),
    # pending_pos
    ("do I have any purchase orders waiting for my response", "pending_pos"),
    ("which orders need my response", "pending_pos"),
    ("do I need to accept any purchase orders", "pending_pos"),
    ("show pending purchase orders", "pending_pos"),
    ("what needs my action", "pending_pos"),
    ("what should I respond to", "pending_pos"),
    ("anything awaiting my approval", "pending_pos"),
    # performance
    ("how is my on time delivery rate", "performance"),
    ("what is my performance", "performance"),
    ("show my delivery performance", "performance"),
    ("how am I doing as a supplier", "performance"),
    ("what is my on-time rate", "performance"),
    ("my performance trend", "performance"),
    ("how have I been performing lately", "performance"),
    # help
    ("what can you do", "help"),
    ("help", "help"),
    ("what can you help me with", "help"),
    ("how does this work", "help"),
    ("what questions can I ask", "help"),
    ("what are you able to answer", "help"),
    # thanks
    ("thank you", "thanks"),
    ("thanks a lot", "thanks"),
    ("appreciate it", "thanks"),
    ("thanks", "thanks"),
    ("cheers", "thanks"),
]

CODE_PATTERN = re.compile(r"\b((?:PO|SHP)-[A-Za-z0-9-]+)\b", re.IGNORECASE)

FALLBACK_MESSAGE = (
    "I can only help with a few specific things here: your shipment status, your purchase order "
    "status, purchase orders waiting for your response, your own delivery performance, or general "
    "help. Could you rephrase your question around one of those?"
)


def extract_code(text: str) -> str | None:
    match = CODE_PATTERN.search(text)
    return match.group(1).upper() if match else None


def is_trained() -> bool:
    return (MODELS_DIR / "chatbot_vectorizer.joblib").exists() and (MODELS_DIR / "chatbot_intent_classifier.joblib").exists()


@lru_cache(maxsize=1)
def _load_model():
    vectorizer = joblib.load(MODELS_DIR / "chatbot_vectorizer.joblib")
    clf = joblib.load(MODELS_DIR / "chatbot_intent_classifier.joblib")
    return vectorizer, clf


MIN_CONFIDENCE = 0.25


def predict_intent(text: str) -> tuple[str, float]:
    """Returns (intent, confidence). Falls back to "unknown" below MIN_CONFIDENCE rather than
    guessing an intent the message doesn't actually match well."""
    vectorizer, clf = _load_model()
    X = vectorizer.transform([text])
    proba = clf.predict_proba(X)[0]
    best_idx = proba.argmax()
    confidence = float(proba[best_idx])
    intent = clf.classes_[best_idx]
    if confidence < MIN_CONFIDENCE:
        return "unknown", confidence
    return intent, confidence
