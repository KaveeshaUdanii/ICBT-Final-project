"""
Smart Contract Automation (module 10).

These functions play the role Hyperledger Fabric chaincode would play in production:
whenever a chain-relevant event happens (a supplier is risk-scored, a shipment's delay
is predicted, stock drops below reorder level...) the matching rule below evaluates its
condition and -- if triggered -- automatically writes an immutable block, raises a
notification, and updates the rule's trigger statistics. No human has to act first.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.blockchain import SmartContractRule
from app.models.enums import NotificationSeverity
from app.models.purchase_order import PurchaseOrder
from app.models.raw_material import RawMaterial
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.services import blockchain_service, notification_service

RULES_SEED: list[dict] = [
    {
        "name": "High Supplier Risk Auto-Flag",
        "trigger_event": "supplier.risk_scored",
        "condition_description": f"Supplier risk_score exceeds {settings.HIGH_RISK_THRESHOLD:.0f}%",
        "action_description": "Flags supplier as HIGH risk, writes an immutable block, and alerts managers.",
    },
    {
        "name": "Low Stock Auto-Reorder Alert",
        "trigger_event": "raw_material.updated",
        "condition_description": "quantity_on_hand falls to or below reorder_level",
        "action_description": "Raises a reorder warning notification and logs the event on-chain.",
    },
    {
        "name": "Shipment Delay Risk Alert",
        "trigger_event": "shipment.delay_predicted",
        "condition_description": "Predicted delay_probability exceeds 60%",
        "action_description": "Notifies managers of the at-risk shipment and records the prediction on-chain.",
    },
    {
        "name": "Anomaly Detected Alert",
        "trigger_event": "shipment.anomaly_detected",
        "condition_description": "Anomaly Detection Model flags a shipment as anomalous",
        "action_description": "Raises a critical notification for immediate investigation.",
    },
    {
        "name": "High-Risk Purchase Order Auto-Flag",
        "trigger_event": "purchase_order.created",
        "condition_description": "Purchase order is placed with a HIGH risk supplier",
        "action_description": "Flags the purchase order for manager review before approval.",
    },
    {
        "name": "High Stockout Risk Alert",
        "trigger_event": "raw_material.stockout_risk_predicted",
        "condition_description": "Stockout Risk Model predicts >60% chance of running out before replenishment",
        "action_description": "Alerts the Warehouse Manager to expedite reordering.",
    },
]


def ensure_rules_seeded(db: Session) -> None:
    existing = {r.name for r in db.execute(select(SmartContractRule)).scalars().all()}
    for rule in RULES_SEED:
        if rule["name"] not in existing:
            db.add(SmartContractRule(**rule))
    db.commit()


def _fire_rule(db: Session, name: str) -> None:
    rule = db.execute(select(SmartContractRule).where(SmartContractRule.name == name)).scalars().first()
    if rule is None:
        return
    rule.times_triggered += 1
    rule.last_triggered_at = datetime.now(timezone.utc)
    db.add(rule)
    db.commit()


def evaluate_supplier_risk(db: Session, supplier: Supplier) -> None:
    blockchain_service.add_block(
        db,
        event_type="supplier.risk_scored",
        payload={
            "entity_type": "supplier",
            "entity_id": supplier.id,
            "risk_score": supplier.risk_score,
            "risk_level": supplier.risk_level.value,
        },
        performed_by="ai_engine",
    )
    if supplier.risk_score > settings.HIGH_RISK_THRESHOLD:
        _fire_rule(db, "High Supplier Risk Auto-Flag")
        notification_service.create_notification(
            db,
            title="High-Risk Supplier Detected",
            message=f"Supplier '{supplier.name}' was auto-flagged with a risk score of "
            f"{supplier.risk_score:.1f}% (threshold: {settings.HIGH_RISK_THRESHOLD:.0f}%). "
            f"Smart contract rule 'High Supplier Risk Auto-Flag' fired automatically.",
            severity=NotificationSeverity.CRITICAL,
            related_entity_type="supplier",
            related_entity_id=supplier.id,
            source="smart_contract",
        )


def evaluate_raw_material_stock(db: Session, material: RawMaterial) -> None:
    blockchain_service.add_block(
        db,
        event_type="raw_material.updated",
        payload={
            "entity_type": "raw_material",
            "entity_id": material.id,
            "quantity_on_hand": material.quantity_on_hand,
            "reorder_level": material.reorder_level,
        },
        performed_by="system",
    )
    if material.needs_reorder:
        _fire_rule(db, "Low Stock Auto-Reorder Alert")
        notification_service.create_notification(
            db,
            title="Reorder Alert",
            message=f"'{material.name}' stock ({material.quantity_on_hand:.1f} {material.unit}) has fallen to or "
            f"below the reorder level ({material.reorder_level:.1f} {material.unit}).",
            severity=NotificationSeverity.WARNING,
            related_entity_type="raw_material",
            related_entity_id=material.id,
            source="smart_contract",
        )


def evaluate_stockout_risk(db: Session, material: RawMaterial) -> None:
    blockchain_service.add_block(
        db,
        event_type="raw_material.stockout_risk_predicted",
        payload={
            "entity_type": "raw_material",
            "entity_id": material.id,
            "stockout_risk_probability": material.stockout_risk_probability,
            "predicted_demand_next_30_days": material.predicted_demand_next_30_days,
        },
        performed_by="ai_engine",
    )
    if (material.stockout_risk_probability or 0) > 0.6:
        _fire_rule(db, "High Stockout Risk Alert")
        notification_service.create_notification(
            db,
            title="High Stockout Risk",
            message=f"'{material.name}' has a {material.stockout_risk_probability * 100:.0f}% chance of stocking "
            f"out before the next replenishment arrives (forecast demand: "
            f"{material.predicted_demand_next_30_days:.0f} {material.unit} over the next 30 days).",
            severity=NotificationSeverity.WARNING,
            related_entity_type="raw_material",
            related_entity_id=material.id,
            source="smart_contract",
        )


def evaluate_shipment_prediction(db: Session, shipment: Shipment) -> None:
    blockchain_service.add_block(
        db,
        event_type="shipment.delay_predicted",
        payload={
            "entity_type": "shipment",
            "entity_id": shipment.id,
            "predicted_delay_days": shipment.predicted_delay_days,
            "delay_probability": shipment.delay_probability,
        },
        performed_by="ai_engine",
    )
    if (shipment.delay_probability or 0) > 0.6:
        _fire_rule(db, "Shipment Delay Risk Alert")
        notification_service.create_notification(
            db,
            title="High Delay Risk Shipment",
            message=f"Shipment '{shipment.shipment_code}' has a {shipment.delay_probability * 100:.0f}% "
            f"chance of delay ({shipment.predicted_delay_days:.1f} days predicted).",
            severity=NotificationSeverity.WARNING,
            related_entity_type="shipment",
            related_entity_id=shipment.id,
            source="smart_contract",
        )
        compute_penalty_exposure(db, shipment, shipment.predicted_delay_days or 0)

    if shipment.is_anomaly:
        blockchain_service.add_block(
            db,
            event_type="shipment.anomaly_detected",
            payload={"entity_type": "shipment", "entity_id": shipment.id, "anomaly_score": shipment.anomaly_score},
            performed_by="ai_engine",
        )
        _fire_rule(db, "Anomaly Detected Alert")
        notification_service.create_notification(
            db,
            title="Anomaly Detected",
            message=f"Shipment '{shipment.shipment_code}' shows an unusual pattern (anomaly score: "
            f"{shipment.anomaly_score:.2f}). Recommend manual review.",
            severity=NotificationSeverity.CRITICAL,
            related_entity_type="shipment",
            related_entity_id=shipment.id,
            source="smart_contract",
        )


def compute_penalty_exposure(db: Session, shipment: Shipment, days_late: float) -> None:
    """On-chain SLA terms: if the linked purchase order carries an agreed penalty_rate_pct
    (percent of order value per day late) and this shipment is running late -- predicted or
    actual -- compute and record the penalty exposure. This is closer to what "smart contract"
    means in the blockchain-supply-chain literature (an agreed term that self-executes on
    breach) than pure event logging."""
    po = shipment.purchase_order
    if po is None or po.penalty_rate_pct <= 0 or days_late <= 0:
        return

    exposure = round(po.total_value * (po.penalty_rate_pct / 100) * days_late, 2)
    po.penalty_exposure = exposure
    db.add(po)
    db.commit()

    blockchain_service.add_block(
        db,
        event_type="purchase_order.penalty_exposure_computed",
        payload={
            "entity_type": "purchase_order",
            "entity_id": po.id,
            "shipment_id": shipment.id,
            "days_late": days_late,
            "penalty_rate_pct": po.penalty_rate_pct,
            "penalty_exposure": exposure,
        },
        performed_by="smart_contract",
    )
    notification_service.create_notification(
        db,
        title="SLA Penalty Exposure Computed",
        message=f"PO '{po.po_number}' is running {days_late:.1f} day(s) late against its agreed "
        f"{po.penalty_rate_pct:.1f}%/day SLA -- computed penalty exposure: ${exposure:,.2f}.",
        severity=NotificationSeverity.WARNING,
        related_entity_type="purchase_order",
        related_entity_id=po.id,
        source="smart_contract",
    )


def evaluate_purchase_order(db: Session, po: PurchaseOrder, supplier: Supplier, log_to_blockchain: bool = True) -> None:
    """log_to_blockchain=False is used by the CSV bulk-import endpoint, which already writes one
    summary block for the whole batch -- the risk auto-flag and manager notification below still
    fire per row either way, only the per-row ledger entry is skipped to avoid ledger bloat."""
    if supplier.risk_level.value == "high":
        po.risk_flag = True
        po.risk_notes = f"Auto-flagged: supplier '{supplier.name}' is HIGH risk (score {supplier.risk_score:.1f}%)."
        db.add(po)
        db.commit()
        _fire_rule(db, "High-Risk Purchase Order Auto-Flag")
        notification_service.create_notification(
            db,
            title="Purchase Order Flagged for Review",
            message=f"PO '{po.po_number}' was placed with high-risk supplier '{supplier.name}' and requires "
            f"manager review before approval.",
            severity=NotificationSeverity.WARNING,
            related_entity_type="purchase_order",
            related_entity_id=po.id,
            source="smart_contract",
        )

    if log_to_blockchain:
        blockchain_service.add_block(
            db,
            event_type="purchase_order.created",
            payload={
                "entity_type": "purchase_order",
                "entity_id": po.id,
                "supplier_id": supplier.id,
                "total_value": po.total_value,
                "risk_flag": po.risk_flag,
            },
            performed_by="system",
        )
