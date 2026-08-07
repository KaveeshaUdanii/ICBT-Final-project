from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_staff
from app.models.blockchain import Block
from app.models.notification import Notification
from app.models.purchase_order import PurchaseOrder
from app.models.raw_material import RawMaterial
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User
from app.services.blockchain_service import verify_chain

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    suppliers = db.execute(select(Supplier)).scalars().all()
    materials = db.execute(select(RawMaterial)).scalars().all()
    shipments = db.execute(select(Shipment)).scalars().all()
    purchase_orders = db.execute(select(PurchaseOrder)).scalars().all()
    block_count = db.execute(select(func.count()).select_from(Block)).scalar_one()
    unread_notifications = db.execute(
        select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))
    ).scalar_one()

    risk_counts = defaultdict(int)
    for s in suppliers:
        risk_counts[s.risk_level.value] += 1

    scored_suppliers = [s for s in suppliers if s.last_scored_at is not None]
    avg_supplier_risk = round(sum(s.risk_score for s in scored_suppliers) / len(scored_suppliers), 1) if scored_suppliers else 0.0

    predicted_shipments = [s for s in shipments if s.delay_probability is not None]
    avg_delay_probability = (
        round(sum(s.delay_probability for s in predicted_shipments) / len(predicted_shipments) * 100, 1)
        if predicted_shipments
        else 0.0
    )
    anomaly_count = sum(1 for s in shipments if s.is_anomaly)

    shipment_status_counts = defaultdict(int)
    for s in shipments:
        shipment_status_counts[s.status.value] += 1

    po_status_counts = defaultdict(int)
    for po in purchase_orders:
        po_status_counts[po.status.value] += 1

    pending_approvals = sum(1 for po in purchase_orders if po.status.value == "pending_approval")

    chain = verify_chain(db)

    return {
        "totals": {
            "suppliers": len(suppliers),
            "raw_materials": len(materials),
            "shipments": len(shipments),
            "purchase_orders": len(purchase_orders),
        },
        "supplier_risk": {
            "low": risk_counts.get("low", 0),
            "medium": risk_counts.get("medium", 0),
            "high": risk_counts.get("high", 0),
            "average_risk_score": avg_supplier_risk,
        },
        "shipments": {
            "by_status": dict(shipment_status_counts),
            "average_delay_probability_pct": avg_delay_probability,
            "anomaly_count": anomaly_count,
        },
        "purchase_orders": {
            "by_status": dict(po_status_counts),
            "flagged_high_risk": sum(1 for po in purchase_orders if po.risk_flag),
            "pending_approval": pending_approvals,
        },
        "inventory": {
            "materials_needing_reorder": sum(1 for m in materials if m.needs_reorder),
        },
        "blockchain": {
            "total_blocks": block_count,
            "chain_valid": chain["is_valid"],
        },
        "notifications": {
            "unread_count": unread_notifications,
        },
    }


@router.get("/risk-heatmap")
def risk_heatmap(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    suppliers = db.execute(select(Supplier)).scalars().all()
    matrix: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for s in suppliers:
        matrix[s.category][s.country].append(s.risk_score)

    cells = []
    for category, countries in matrix.items():
        for country, scores in countries.items():
            cells.append(
                {
                    "category": category,
                    "country": country,
                    "average_risk_score": round(sum(scores) / len(scores), 1),
                    "supplier_count": len(scores),
                }
            )
    return {"cells": cells}


@router.get("/delay-trend")
def delay_trend(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    shipments = db.execute(select(Shipment).where(Shipment.predicted_delay_days.is_not(None))).scalars().all()
    monthly: dict[str, list[float]] = defaultdict(list)
    for s in shipments:
        key = s.expected_delivery_date.strftime("%Y-%m")
        monthly[key].append(s.predicted_delay_days)

    points = [
        {"month": month, "average_predicted_delay_days": round(sum(vals) / len(vals), 2), "shipment_count": len(vals)}
        for month, vals in sorted(monthly.items())
    ]
    return {"points": points}


@router.get("/warehouse-dashboard")
def warehouse_dashboard(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    """Inventory-centric KPIs for the Warehouse Manager dashboard -- deliberately excludes
    supplier risk scoring / blockchain internals, which aren't part of warehouse operations."""
    materials = db.execute(select(RawMaterial)).scalars().all()
    shipments = db.execute(
        select(Shipment).where(Shipment.status.in_(["pending", "in_transit"]))
    ).scalars().all()

    needing_reorder = [m for m in materials if m.needs_reorder]
    category_counts = defaultdict(int)
    for m in materials:
        category_counts[m.category] += 1

    return {
        "totals": {
            "materials": len(materials),
            "needing_reorder": len(needing_reorder),
            "incoming_shipments": len(shipments),
        },
        "materials_by_category": dict(category_counts),
        "reorder_list": [
            {
                "id": m.id,
                "name": m.name,
                "unit": m.unit,
                "quantity_on_hand": m.quantity_on_hand,
                "reorder_level": m.reorder_level,
            }
            for m in sorted(needing_reorder, key=lambda m: m.quantity_on_hand / max(m.reorder_level, 0.01))[:10]
        ],
    }


@router.get("/my-dashboard")
def my_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Supplier-portal summary -- an external party only ever sees data scoped to their
    own linked Supplier record, never company-wide analytics or other suppliers."""
    if current_user.role.value != "supplier" or current_user.supplier_id is None:
        return {
            "supplier": None,
            "shipments": {"total": 0, "by_status": {}},
            "purchase_orders": {"total": 0, "by_status": {}},
        }

    supplier = db.get(Supplier, current_user.supplier_id)
    shipments = db.execute(select(Shipment).where(Shipment.supplier_id == current_user.supplier_id)).scalars().all()
    purchase_orders = db.execute(
        select(PurchaseOrder).where(PurchaseOrder.supplier_id == current_user.supplier_id)
    ).scalars().all()

    shipment_status_counts = defaultdict(int)
    for s in shipments:
        shipment_status_counts[s.status.value] += 1
    po_status_counts = defaultdict(int)
    for po in purchase_orders:
        po_status_counts[po.status.value] += 1

    return {
        "supplier": {
            "id": supplier.id,
            "name": supplier.name,
            "on_time_delivery_rate": supplier.on_time_delivery_rate,
            "avg_lead_time_days": supplier.avg_lead_time_days,
        }
        if supplier
        else None,
        "shipments": {"total": len(shipments), "by_status": dict(shipment_status_counts)},
        "purchase_orders": {"total": len(purchase_orders), "by_status": dict(po_status_counts)},
    }
