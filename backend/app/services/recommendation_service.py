"""Intelligent Recommendation Engine (module 7)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.raw_material import RawMaterial
from app.models.recommendation import Recommendation
from app.models.supplier import Supplier


def recommend_alternative_suppliers(db: Session, supplier: Supplier, top_n: int = 2) -> list[Recommendation]:
    """When a supplier is risky, suggest lower-risk active alternatives in the same category --
    same country preferred (shorter/simpler logistics) but not required, since requiring an exact
    country match could leave a niche-country supplier with zero candidates."""
    candidates = (
        db.execute(
            select(Supplier)
            .where(
                Supplier.category == supplier.category,
                Supplier.id != supplier.id,
                Supplier.is_active.is_(True),
                Supplier.risk_score < supplier.risk_score,
            )
            # same-country candidates first (False sorts before True), then lowest risk within each group
            .order_by((Supplier.country != supplier.country), Supplier.risk_score.asc())
            .limit(top_n)
        )
        .scalars()
        .all()
    )

    created = []
    for alt in candidates:
        risk_gap = supplier.risk_score - alt.risk_score
        same_country = alt.country == supplier.country
        text = (
            f"'{alt.name}' ({alt.country}) is recommended over '{supplier.name}' because its predicted risk score "
            f"is {risk_gap:.0f} points lower ({alt.risk_score:.0f}% vs {supplier.risk_score:.0f}%) for the same "
            f"'{supplier.category}' category"
            + (", in the same country." if same_country else f" (based in {alt.country} vs {supplier.country}).")
        )
        rec = Recommendation(
            entity_type="supplier",
            entity_id=supplier.id,
            recommendation_text=text,
            recommended_supplier_id=alt.id,
            confidence=min(0.5 + risk_gap / 100, 0.98),
        )
        db.add(rec)
        created.append(rec)
    if created:
        db.commit()
        for r in created:
            db.refresh(r)
    return created


def recommend_reorder(db: Session, material: RawMaterial) -> Recommendation | None:
    """Suggests reorder quantity/timing once stock falls to/below the reorder level."""
    if not material.needs_reorder:
        return None

    target_stock = material.reorder_level * 2
    suggested_quantity = max(target_stock - material.quantity_on_hand, material.reorder_level)
    text = (
        f"Reorder '{material.name}' now: current stock ({material.quantity_on_hand:.0f} {material.unit}) is at or "
        f"below the reorder level ({material.reorder_level:.0f} {material.unit}). Suggested order quantity: "
        f"{suggested_quantity:.0f} {material.unit}, allowing for the supplier's {material.lead_time_days}-day lead time."
    )
    rec = Recommendation(
        entity_type="raw_material",
        entity_id=material.id,
        recommendation_text=text,
        recommended_supplier_id=material.supplier_id,
        confidence=0.9,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
