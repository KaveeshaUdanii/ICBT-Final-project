import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import data_entry_check
from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin
from app.models.enums import NotificationSeverity, PurchaseOrderStatus, UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.raw_material import RawMaterial
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderExternalRead,
    PurchaseOrderRead,
    PurchaseOrderRespond,
    PurchaseOrderUpdate,
)
from app.services import blockchain_service, change_log_service, csv_import_service, notification_service, smart_contract_service

router = APIRouter(prefix="/api/purchase-orders", tags=["Purchase Order Management"])


def _assert_supplier_can_view(user: User, supplier_id: int) -> None:
    if user.role == UserRole.SUPPLIER and user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")


def _to_read(po: PurchaseOrder, current_user: User) -> dict:
    # response_model=None on every route below: see suppliers.py's _to_read for why a
    # Union[PurchaseOrderExternalRead, PurchaseOrderRead] response_model isn't used here.
    schema = PurchaseOrderExternalRead if current_user.role == UserRole.SUPPLIER else PurchaseOrderRead
    data = schema.model_validate(po).model_dump(mode="json")
    data["raw_material_name"] = po.raw_material.name if po.raw_material else ""
    return data


@router.get("", response_model=None)
def list_purchase_orders(
    status_filter: str | None = None,
    supplier_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PurchaseOrder)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)

    if current_user.role == UserRole.SUPPLIER:
        stmt = stmt.where(PurchaseOrder.supplier_id == current_user.supplier_id)
    elif supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)

    pos = db.execute(stmt.order_by(PurchaseOrder.id.desc())).scalars().all()
    return [_to_read(po, current_user) for po in pos]


@router.get("/{po_id}", response_model=None)
def get_purchase_order(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    _assert_supplier_can_view(current_user, po.supplier_id)
    return _to_read(po, current_user)


@router.post("", response_model=None, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not exist.")
    material = db.get(RawMaterial, payload.raw_material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Raw material does not exist.")

    flagged, warning = data_entry_check.check_purchase_order(
        db, payload.supplier_id, payload.quantity, payload.unit_price
    )

    po = PurchaseOrder(
        **payload.model_dump(), status=PurchaseOrderStatus.PENDING_APPROVAL, data_entry_flag=flagged, data_entry_warning=warning
    )
    db.add(po)
    db.commit()
    db.refresh(po)

    if flagged:
        notification_service.create_notification(
            db,
            title="Unusual Purchase Order Detected",
            message=f"PO '{po.po_number}': {warning}",
            severity=NotificationSeverity.WARNING,
            related_entity_type="purchase_order",
            related_entity_id=po.id,
            source="ai_engine",
        )

    smart_contract_service.evaluate_purchase_order(db, po, supplier)
    db.refresh(po)
    return _to_read(po, current_user)


@router.post("/{po_id}/respond", response_model=None)
def respond_to_purchase_order(
    po_id: int,
    payload: PurchaseOrderRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A Supplier account accepting or declining a PO -- the single biggest thing that turns
    the portal from a read-only viewer into something the supplier actually acts on."""
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    if current_user.role != UserRole.SUPPLIER or current_user.supplier_id != po.supplier_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the linked supplier can respond to this PO.")
    if po.supplier_response != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This purchase order has already been responded to.")

    po.supplier_response = payload.response
    po.decline_reason = payload.reason if payload.response == "declined" else ""
    db.add(po)
    db.commit()
    db.refresh(po)

    blockchain_service.add_block(
        db,
        event_type="purchase_order.supplier_responded",
        payload={
            "entity_type": "purchase_order",
            "entity_id": po.id,
            "response": payload.response,
            "reason": payload.reason,
        },
        performed_by=current_user.email,
    )
    notification_service.create_notification(
        db,
        title=f"Supplier {'Accepted' if payload.response == 'accepted' else 'Declined'} PO '{po.po_number}'",
        message=(
            f"'{po.supplier.name if po.supplier else 'Supplier'}' {payload.response} PO '{po.po_number}'"
            + (f": {payload.reason}" if payload.response == "declined" and payload.reason else ".")
        ),
        severity=NotificationSeverity.WARNING if payload.response == "declined" else NotificationSeverity.INFO,
        related_entity_type="purchase_order",
        related_entity_id=po.id,
        source="system",
    )
    return _to_read(po, current_user)


@router.post("/{po_id}/approve", response_model=None, dependencies=[Depends(require_manager_or_admin)])
def approve_purchase_order(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending purchase orders can be approved.")

    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by = current_user.id
    db.add(po)
    db.commit()
    db.refresh(po)

    blockchain_service.add_block(
        db,
        event_type="purchase_order.approved",
        payload={"entity_type": "purchase_order", "entity_id": po.id, "approved_by": current_user.email},
        performed_by=current_user.email,
    )
    return _to_read(po, current_user)


@router.post("/{po_id}/reject", response_model=None, dependencies=[Depends(require_manager_or_admin)])
def reject_purchase_order(
    po_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending purchase orders can be rejected.")

    po.status = PurchaseOrderStatus.REJECTED
    po.risk_notes = (po.risk_notes + f" | Rejected: {reason}").strip(" |")
    db.add(po)
    db.commit()
    db.refresh(po)

    blockchain_service.add_block(
        db,
        event_type="purchase_order.rejected",
        payload={"entity_type": "purchase_order", "entity_id": po.id, "reason": reason},
        performed_by=current_user.email,
    )
    return _to_read(po, current_user)


@router.put("/{po_id}", response_model=None)
def update_purchase_order(
    po_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")

    before = {"quantity": po.quantity, "expected_delivery_date": po.expected_delivery_date, "unit_price": po.unit_price}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(po, field, value)
    db.add(po)
    db.commit()
    db.refresh(po)

    change_log_service.log_field_changes(
        db,
        entity_type="purchase_order",
        entity_id=po.id,
        entity_label=f"Purchase Order '{po.po_number}'",
        supplier_id=po.supplier_id,
        before=before,
        after={"quantity": po.quantity, "expected_delivery_date": po.expected_delivery_date, "unit_price": po.unit_price},
        changed_by=current_user.email,
    )
    return _to_read(po, current_user)


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(po_id: int, db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    db.delete(po)
    db.commit()
    return None


@router.post("/import-csv")
async def import_purchase_orders_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Bulk-imports purchase orders from a CSV export. Accepts `supplier_id`/`supplier_name` and
    `raw_material_id`/`raw_material_name` (each resolved by exact name match when the id isn't
    given). This doesn't reuse the generic csv_import_service.import_csv helper because, unlike
    the other three entities, a purchase order also needs the high-risk-supplier auto-flag +
    manager notification smart_contract_service.evaluate_purchase_order runs on manual creation --
    and that function commits internally, which would break the per-row SAVEPOINT isolation the
    generic helper relies on. So each row is imported inside its own savepoint first (exactly like
    the other entities), and only *after* that whole loop is safely committed does a second pass
    run the per-row business rule (safe now that we're back at the top-level transaction), with
    its own blockchain logging suppressed in favor of one summary block for the batch."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file.")
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse CSV: {exc}") from exc
    if df.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file has no data rows.")

    allowed_fields = set(PurchaseOrderCreate.model_fields.keys())
    imported_ids: list[tuple[int, int]] = []  # (po_id, supplier_id)
    errors: list[dict] = []

    for i, row in df.iterrows():
        row_dict = row.to_dict()
        try:
            with db.begin_nested():
                payload_dict = csv_import_service.row_payload(row_dict, allowed_fields)

                supplier_name = csv_import_service.cell(row_dict, "supplier_name")
                if "supplier_id" not in payload_dict and supplier_name:
                    supplier = db.execute(select(Supplier).where(Supplier.name == supplier_name)).scalars().first()
                    if not supplier:
                        raise ValueError(f"Supplier '{supplier_name}' not found.")
                    payload_dict["supplier_id"] = supplier.id

                material_name = csv_import_service.cell(row_dict, "raw_material_name")
                if "raw_material_id" not in payload_dict and material_name:
                    material = db.execute(select(RawMaterial).where(RawMaterial.name == material_name)).scalars().first()
                    if not material:
                        raise ValueError(f"Raw material '{material_name}' not found.")
                    payload_dict["raw_material_id"] = material.id

                payload = PurchaseOrderCreate(**payload_dict)
                if not db.get(Supplier, payload.supplier_id):
                    raise ValueError(f"Supplier id {payload.supplier_id} does not exist.")
                if not db.get(RawMaterial, payload.raw_material_id):
                    raise ValueError(f"Raw material id {payload.raw_material_id} does not exist.")

                po = PurchaseOrder(**payload.model_dump(), status=PurchaseOrderStatus.PENDING_APPROVAL)
                db.add(po)
                db.flush()
                imported_ids.append((po.id, payload.supplier_id))
        except Exception as exc:  # noqa: BLE001 -- any row-level failure is reported, not fatal
            if len(errors) < csv_import_service.MAX_REPORTED_ERRORS:
                errors.append({"row": int(i) + 2, "error": str(exc)})

    db.commit()

    for po_id, supplier_id in imported_ids:
        po = db.get(PurchaseOrder, po_id)
        supplier = db.get(Supplier, supplier_id)
        if po and supplier:
            smart_contract_service.evaluate_purchase_order(db, po, supplier, log_to_blockchain=False)

    blockchain_service.add_block(
        db,
        event_type="purchase_order.bulk_imported",
        payload={"entity_type": "purchase_order", "imported": len(imported_ids), "failed": len(df) - len(imported_ids)},
        performed_by=current_user.email,
    )

    return {"imported": len(imported_ids), "failed": len(df) - len(imported_ids), "errors": errors}
