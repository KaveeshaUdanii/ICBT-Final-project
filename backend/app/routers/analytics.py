from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_staff
from app.models.blockchain import Block
from app.models.enums import ShipmentStatus
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
            "purchase_orders": {"total": 0, "by_status": {}, "total_value": 0.0},
            "upcoming_shipments": [],
            "recent_purchase_orders": [],
            "pending_response_purchase_orders": [],
            "performance_trend": [],
            "materials_demand_forecast": {"total_next_30_days": 0.0, "by_material": []},
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

    # Useful, self-serve supplier features -- factual records of this supplier's own
    # transaction history (a vendor scorecard + upcoming-work view), never the AI Risk
    # Engine's internal risk_score/risk_level classification of them or any other supplier's
    # data. Kept intentionally small (top 5 of each) -- this is a glance-and-go summary, not
    # a replacement for the (already backend-scoped) full Shipments/Purchase Orders pages.
    open_statuses = {ShipmentStatus.PENDING, ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELAYED}
    upcoming_shipments = sorted(
        (s for s in shipments if s.status in open_statuses),
        key=lambda s: s.expected_delivery_date,
    )[:5]
    recent_purchase_orders = sorted(purchase_orders, key=lambda po: po.order_date, reverse=True)[:5]
    total_po_value = sum(po.total_value for po in purchase_orders)

    pending_response = [
        po for po in purchase_orders if po.supplier_response == "pending" and po.status.value != "rejected"
    ]

    # Own performance trend: factual, computed straight from this supplier's own delivered
    # shipments (on-time rate + average delay), grouped by month -- never the internal AI
    # risk_score/risk_level. Same "monitor reliability over time" gap as the admin-side risk
    # history, answered from the supplier's own side instead.
    delivered = [s for s in shipments if s.actual_delivery_date is not None]
    monthly_shipments: dict[str, list] = defaultdict(list)
    for s in delivered:
        monthly_shipments[s.expected_delivery_date.strftime("%Y-%m")].append(s)
    performance_trend = [
        {
            "month": month,
            "on_time_rate": round(sum(1 for s in ships if (s.actual_delay_days or 0) <= 0) / len(ships), 3),
            "average_delay_days": round(sum(max(s.actual_delay_days or 0, 0) for s in ships) / len(ships), 2),
            "shipment_count": len(ships),
        }
        for month, ships in sorted(monthly_shipments.items())
    ]

    # Aggregated forward demand for materials linked to this supplier -- name + forecast only,
    # never the full Raw Materials catalog (quantity_on_hand, reorder_level, unit_cost stay
    # internal-only, see RawMaterialRead vs this hand-built subset).
    materials = db.execute(select(RawMaterial).where(RawMaterial.supplier_id == current_user.supplier_id)).scalars().all()
    forecasted = [m for m in materials if m.predicted_demand_next_30_days is not None]
    materials_demand_forecast = {
        "total_next_30_days": round(sum(m.predicted_demand_next_30_days for m in forecasted), 1),
        "by_material": [
            {"name": m.name, "unit": m.unit, "predicted_demand_next_30_days": m.predicted_demand_next_30_days}
            for m in sorted(forecasted, key=lambda m: m.predicted_demand_next_30_days, reverse=True)
        ],
    }

    return {
        "supplier": {
            "id": supplier.id,
            "name": supplier.name,
            "on_time_delivery_rate": supplier.on_time_delivery_rate,
            "defect_rate": supplier.defect_rate,
            "cancellation_rate": supplier.cancellation_rate,
            "avg_lead_time_days": supplier.avg_lead_time_days,
            "order_volume_last_year": supplier.order_volume_last_year,
            "contact_email": supplier.contact_email,
            "contact_phone": supplier.contact_phone,
        }
        if supplier
        else None,
        "shipments": {"total": len(shipments), "by_status": dict(shipment_status_counts)},
        "purchase_orders": {
            "total": len(purchase_orders),
            "by_status": dict(po_status_counts),
            "total_value": round(total_po_value, 2),
        },
        "upcoming_shipments": [
            {
                "shipment_code": s.shipment_code,
                "status": s.status.value,
                "expected_delivery_date": s.expected_delivery_date.isoformat(),
                "quantity": s.quantity,
            }
            for s in upcoming_shipments
        ],
        "recent_purchase_orders": [
            {
                "po_number": po.po_number,
                "status": po.status.value,
                "order_date": po.order_date.isoformat(),
                "expected_delivery_date": po.expected_delivery_date.isoformat(),
                "total_value": po.total_value,
            }
            for po in recent_purchase_orders
        ],
        "pending_response_purchase_orders": [
            {
                "id": po.id,
                "po_number": po.po_number,
                "status": po.status.value,
                "expected_delivery_date": po.expected_delivery_date.isoformat(),
                "total_value": po.total_value,
            }
            for po in pending_response
        ],
        "performance_trend": performance_trend,
        "materials_demand_forecast": materials_demand_forecast,
    }
