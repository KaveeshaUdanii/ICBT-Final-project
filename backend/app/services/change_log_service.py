"""
Change-notification log for Purchase Order / Shipment spec edits.

The literature this project cites (Tharuka, 2026) found that *late change notifications* --
a quantity or delivery-date edit nobody downstream was told about in time -- are a specific,
named cause of line stoppages. This module diffs the fields that matter (quantity,
expected_delivery_date) on every update, writes an immutable audit-trail entry via the
existing blockchain ledger, and raises a targeted Notification to the other party (a
supplier's own portal user if staff made the change, or a broadcast to staff if the
supplier did), instead of the change happening silently.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import NotificationSeverity, UserRole
from app.models.user import User
from app.services import blockchain_service, notification_service

TRACKED_FIELDS = ("quantity", "expected_delivery_date", "unit_price")


def log_field_changes(
    db: Session,
    entity_type: str,
    entity_id: int,
    entity_label: str,
    supplier_id: int,
    before: dict,
    after: dict,
    changed_by: str,
) -> None:
    diffs = {
        field: {"old": before[field], "new": after[field]}
        for field in TRACKED_FIELDS
        if field in before and field in after and before[field] != after[field]
    }
    if not diffs:
        return

    blockchain_service.add_block(
        db,
        event_type=f"{entity_type}.spec_changed",
        payload={"entity_type": entity_type, "entity_id": entity_id, "changes": diffs},
        performed_by=changed_by,
    )

    change_summary = "; ".join(
        f"{field.replace('_', ' ')}: {d['old']} → {d['new']}" for field, d in diffs.items()
    )
    message = f"{entity_label} changed -- {change_summary}."

    supplier_user = db.execute(
        select(User).where(User.role == UserRole.SUPPLIER, User.supplier_id == supplier_id)
    ).scalars().first()

    if changed_by == (supplier_user.email if supplier_user else None):
        # Supplier made the change -- notify internal staff (broadcast, same as other
        # smart-contract alerts staff already see).
        notification_service.create_notification(
            db,
            title=f"{entity_label} Updated by Supplier",
            message=message,
            severity=NotificationSeverity.WARNING,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            source="system",
        )
    elif supplier_user:
        # Staff made the change -- notify that supplier's own portal account directly, not a
        # broadcast (a supplier must never see another supplier's notifications).
        notification_service.create_notification(
            db,
            title=f"{entity_label} Updated",
            message=message,
            severity=NotificationSeverity.WARNING,
            user_id=supplier_user.id,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            source="system",
        )
