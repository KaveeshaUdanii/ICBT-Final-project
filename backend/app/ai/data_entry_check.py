"""
Data-entry anomaly check (real-time, at creation).

Distinct from the post-hoc shipment Anomaly Detection model (Isolation Forest, module 6),
which only scores a shipment *after* it already exists. This module runs at the moment a
Purchase Order or Shipment is created -- before the record is ever acted on -- and flags a
quantity or unit price that is implausible for *this* supplier/category, the way a second
pair of eyes would catch a typo (an extra zero, a wrong item code pulling the wrong unit
price) before it causes a line stoppage. Directly targets the human-error/data-entry problem
the project's own literature review identifies as under-addressed.

Statistics-based (mean/std z-score) rather than a trained model: with only a handful of
historical rows for a brand-new supplier, a trained classifier has nothing to learn from,
while a z-score check degrades gracefully and is fully transparent about why something was
flagged -- itself a form of explainability. Falls back from this-supplier's own history, to
the same category, to the whole dataset, so a supplier with little order history of their own
still gets a meaningful check instead of silently skipping it.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

MIN_SAMPLES_FOR_CHECK = 5
Z_SCORE_THRESHOLD = 3.0


@dataclass
class FieldCheck:
    field: str
    value: float
    mean: float
    stdev: float
    z_score: float
    scope: str  # "this supplier" | "this category" | "all suppliers"

    @property
    def is_outlier(self) -> bool:
        return abs(self.z_score) >= Z_SCORE_THRESHOLD


def _z_score_checks(
    value_by_field: dict[str, float],
    history_tiers_by_field: dict[str, list[tuple[str, list[float]]]],
) -> list[FieldCheck]:
    """history_tiers_by_field maps each field to an ordered list of (scope_label, values) --
    tried in order until one has enough samples to compute meaningful statistics from."""
    checks = []
    for field, value in value_by_field.items():
        for scope, raw_history in history_tiers_by_field.get(field, []):
            history = [v for v in raw_history if v is not None]
            if len(history) < MIN_SAMPLES_FOR_CHECK:
                continue
            mean = statistics.mean(history)
            stdev = statistics.pstdev(history) or 1e-6  # avoid div-by-zero on a perfectly uniform history
            z = (value - mean) / stdev
            checks.append(FieldCheck(field=field, value=value, mean=mean, stdev=stdev, z_score=z, scope=scope))
            break  # found a usable tier for this field -- don't also check broader tiers
    return checks


def _format_warning(entity_label: str, checks: list[FieldCheck]) -> str:
    outliers = [c for c in checks if c.is_outlier]
    parts = [
        f"{c.field.replace('_', ' ')} of {c.value:,.2f} is unusual for {c.scope} "
        f"(typical: {c.mean:,.2f} ± {c.stdev:,.2f})"
        for c in outliers
    ]
    return f"Data-entry check on this {entity_label}: " + "; ".join(parts) + ". Please double-check before proceeding."


def check_purchase_order(db: Session, supplier_id: int, quantity: float, unit_price: float) -> tuple[bool, str]:
    from app.models.purchase_order import PurchaseOrder
    from app.models.supplier import Supplier

    supplier = db.get(Supplier, supplier_id)
    category = supplier.category if supplier else None

    own_rows = db.execute(
        select(PurchaseOrder.quantity, PurchaseOrder.unit_price).where(PurchaseOrder.supplier_id == supplier_id)
    ).all()
    category_rows = (
        db.execute(
            select(PurchaseOrder.quantity, PurchaseOrder.unit_price)
            .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
            .where(Supplier.category == category)
        ).all()
        if category
        else []
    )
    all_rows = db.execute(select(PurchaseOrder.quantity, PurchaseOrder.unit_price)).all()

    tiers = {
        "quantity": [
            ("this supplier", [r[0] for r in own_rows]),
            ("this category", [r[0] for r in category_rows]),
            ("all suppliers", [r[0] for r in all_rows]),
        ],
        "unit_price": [
            ("this supplier", [r[1] for r in own_rows]),
            ("this category", [r[1] for r in category_rows]),
            ("all suppliers", [r[1] for r in all_rows]),
        ],
    }
    checks = _z_score_checks({"quantity": quantity, "unit_price": unit_price}, tiers)
    if not any(c.is_outlier for c in checks):
        return False, ""
    return True, _format_warning("purchase order", checks)


def check_shipment(db: Session, supplier_id: int, quantity: float) -> tuple[bool, str]:
    from app.models.shipment import Shipment
    from app.models.supplier import Supplier

    supplier = db.get(Supplier, supplier_id)
    category = supplier.category if supplier else None

    own_rows = db.execute(select(Shipment.quantity).where(Shipment.supplier_id == supplier_id)).all()
    category_rows = (
        db.execute(
            select(Shipment.quantity).join(Supplier, Supplier.id == Shipment.supplier_id).where(Supplier.category == category)
        ).all()
        if category
        else []
    )
    all_rows = db.execute(select(Shipment.quantity)).all()

    tiers = {
        "quantity": [
            ("this supplier", [r[0] for r in own_rows]),
            ("this category", [r[0] for r in category_rows]),
            ("all suppliers", [r[0] for r in all_rows]),
        ],
    }
    checks = _z_score_checks({"quantity": quantity}, tiers)
    if not any(c.is_outlier for c in checks):
        return False, ""
    return True, _format_warning("shipment", checks)
