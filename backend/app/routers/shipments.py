from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import date, datetime, timezone

from app.ai import data_entry_check
from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin, require_staff
from app.models.enums import NotificationSeverity, ShipmentStatus, UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.shipment import ShipmentCreate, ShipmentExternalRead, ShipmentRead, ShipmentShip, ShipmentUpdate
from app.services import blockchain_service, change_log_service, csv_import_service, notification_service, smart_contract_service

router = APIRouter(prefix="/api/shipments", tags=["Shipment Management"])


def _to_read(shipment: Shipment, current_user: User) -> dict:
    # response_model=None on every route below: see suppliers.py's _to_read for why a
    # Union[ShipmentExternalRead, ShipmentRead] response_model isn't used here -- the
    # narrower external schema would validate (and get silently applied to) internal
    # callers too, since its fields are a strict subset of the full schema's.
    if current_user.role == UserRole.SUPPLIER:
        data = ShipmentExternalRead.model_validate(shipment).model_dump(mode="json")
        data["actual_delay_days"] = shipment.actual_delay_days
        return data
    data = ShipmentRead.model_validate(shipment).model_dump(mode="json")
    data["actual_delay_days"] = shipment.actual_delay_days
    return data


def _assert_supplier_can_view(user: User, supplier_id: int) -> None:
    """A supplier-portal account may only ever see its own shipments -- this is an
    external party, so cross-supplier visibility would leak competitor information."""
    if user.role == UserRole.SUPPLIER and user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")


@router.get("", response_model=None)
def list_shipments(
    status_filter: str | None = None,
    supplier_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Shipment)
    if status_filter:
        stmt = stmt.where(Shipment.status == status_filter)

    if current_user.role == UserRole.SUPPLIER:
        # Ignore any caller-supplied supplier_id -- a supplier account can only ever
        # see shipments tied to its own linked Supplier record, never another's.
        stmt = stmt.where(Shipment.supplier_id == current_user.supplier_id)
    elif supplier_id:
        stmt = stmt.where(Shipment.supplier_id == supplier_id)

    shipments = db.execute(stmt.order_by(Shipment.id.desc())).scalars().all()
    return [_to_read(s, current_user) for s in shipments]


@router.get("/{shipment_id}", response_model=None)
def get_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    _assert_supplier_can_view(current_user, shipment.supplier_id)
    return _to_read(shipment, current_user)


@router.post("", response_model=None, status_code=status.HTTP_201_CREATED)
def create_shipment(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not exist.")
    if payload.purchase_order_id and not db.get(PurchaseOrder, payload.purchase_order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase order does not exist.")

    flagged, warning = data_entry_check.check_shipment(db, payload.supplier_id, payload.quantity)

    shipment = Shipment(**payload.model_dump(), data_entry_flag=flagged, data_entry_warning=warning)
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    if flagged:
        notification_service.create_notification(
            db,
            title="Unusual Shipment Detected",
            message=f"Shipment '{shipment.shipment_code}': {warning}",
            severity=NotificationSeverity.WARNING,
            related_entity_type="shipment",
            related_entity_id=shipment.id,
            source="ai_engine",
        )

    blockchain_service.add_block(
        db,
        event_type="shipment.created",
        payload={"entity_type": "shipment", "entity_id": shipment.id, "shipment_code": shipment.shipment_code},
        performed_by=current_user.email,
    )
    return _to_read(shipment, current_user)


@router.put("/{shipment_id}", response_model=None)
def update_shipment(
    shipment_id: int,
    payload: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")

    before = {"quantity": shipment.quantity, "expected_delivery_date": shipment.expected_delivery_date}
    was_supplier_confirmed = shipment.supplier_confirmed_delivery
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)

    marking_delivered_now = payload.status == ShipmentStatus.DELIVERED
    if marking_delivered_now:
        shipment.staff_confirmed_delivery = True
        shipment.staff_confirmed_delivery_at = datetime.now(timezone.utc)

    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    change_log_service.log_field_changes(
        db,
        entity_type="shipment",
        entity_id=shipment.id,
        entity_label=f"Shipment '{shipment.shipment_code}'",
        supplier_id=shipment.supplier_id,
        before=before,
        after={"quantity": shipment.quantity, "expected_delivery_date": shipment.expected_delivery_date},
        changed_by=current_user.email,
    )

    if marking_delivered_now and not was_supplier_confirmed:
        # Staff force-marked delivery without the supplier having confirmed their side --
        # an operational necessity that must still be an auditable override, not silently
        # indistinguishable from the normal two-party-confirmed path.
        blockchain_service.add_block(
            db,
            event_type="shipment.delivered_without_supplier_confirmation",
            payload={"entity_type": "shipment", "entity_id": shipment.id, "overridden_by": current_user.email},
            performed_by=current_user.email,
        )

    event = "shipment.delivered" if shipment.status.value == "delivered" else "shipment.updated"
    blockchain_service.add_block(
        db,
        event_type=event,
        payload={
            "entity_type": "shipment",
            "entity_id": shipment.id,
            "status": shipment.status.value,
            "actual_delay_days": shipment.actual_delay_days,
        },
        performed_by=current_user.email,
    )

    if shipment.status == ShipmentStatus.DELIVERED and (shipment.actual_delay_days or 0) > 0:
        smart_contract_service.compute_penalty_exposure(db, shipment, float(shipment.actual_delay_days))

    return _to_read(shipment, current_user)


@router.post("/{shipment_id}/ship", response_model=None)
def ship_shipment(
    shipment_id: int,
    payload: ShipmentShip,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The supplier marking their own shipment as sent, with carrier/tracking info -- splits
    the workflow the way it actually works between two organizations, instead of only
    internal staff ever being able to touch shipment status."""
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    if current_user.role != UserRole.SUPPLIER or current_user.supplier_id != shipment.supplier_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the linked supplier can ship this shipment.")
    if shipment.status not in (ShipmentStatus.PENDING, ShipmentStatus.DELAYED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a pending or delayed shipment can be marked shipped.")

    shipment.status = ShipmentStatus.IN_TRANSIT
    shipment.carrier = payload.carrier
    shipment.tracking_number = payload.tracking_number
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    blockchain_service.add_block(
        db,
        event_type="shipment.shipped_by_supplier",
        payload={
            "entity_type": "shipment",
            "entity_id": shipment.id,
            "carrier": payload.carrier,
            "tracking_number": payload.tracking_number,
        },
        performed_by=current_user.email,
    )
    notification_service.create_notification(
        db,
        title="Shipment Marked In Transit by Supplier",
        message=f"'{shipment.shipment_code}' was marked in transit by its supplier"
        + (f" (carrier: {payload.carrier})" if payload.carrier else "") + ".",
        severity=NotificationSeverity.INFO,
        related_entity_type="shipment",
        related_entity_id=shipment.id,
        source="system",
    )
    return _to_read(shipment, current_user)


@router.post("/{shipment_id}/confirm-delivery", response_model=None)
def confirm_delivery(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Multi-party delivery confirmation: both the supplier and internal staff confirm their
    side independently; status only auto-advances to "delivered" once both have. Catches the
    exact "wrong quantity/status entered under pressure by one side" error the literature
    describes, since neither party can unilaterally finalize delivery."""
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")

    is_supplier = current_user.role == UserRole.SUPPLIER
    if is_supplier and current_user.supplier_id != shipment.supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    if not is_supplier and current_user.role not in (UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER, UserRole.WAREHOUSE_MANAGER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to confirm delivery.")

    now = datetime.now(timezone.utc)
    if is_supplier:
        shipment.supplier_confirmed_delivery = True
        shipment.supplier_confirmed_delivery_at = now
    else:
        shipment.staff_confirmed_delivery = True
        shipment.staff_confirmed_delivery_at = now

    both_confirmed = shipment.supplier_confirmed_delivery and shipment.staff_confirmed_delivery
    if both_confirmed and shipment.status != ShipmentStatus.DELIVERED:
        shipment.status = ShipmentStatus.DELIVERED
        if shipment.actual_delivery_date is None:
            shipment.actual_delivery_date = date.today()

    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    blockchain_service.add_block(
        db,
        event_type="shipment.delivery_confirmed",
        payload={
            "entity_type": "shipment",
            "entity_id": shipment.id,
            "confirmed_by_role": current_user.role.value,
            "both_confirmed": both_confirmed,
        },
        performed_by=current_user.email,
    )

    if both_confirmed and (shipment.actual_delay_days or 0) > 0:
        smart_contract_service.compute_penalty_exposure(db, shipment, float(shipment.actual_delay_days))

    return _to_read(shipment, current_user)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    db.delete(shipment)
    db.commit()
    return None


@router.post("/import-csv")
async def import_shipments_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Bulk-imports shipments from a CSV export. Accepts either a `supplier_id` column or a
    human-friendly `supplier_name` column (resolved by exact name match)."""
    allowed_fields = set(ShipmentCreate.model_fields.keys())

    def build(row: dict):
        payload_dict = csv_import_service.row_payload(row, allowed_fields)
        supplier_name = csv_import_service.cell(row, "supplier_name")
        if "supplier_id" not in payload_dict and supplier_name:
            supplier = db.execute(select(Supplier).where(Supplier.name == supplier_name)).scalars().first()
            if not supplier:
                raise ValueError(f"Supplier '{supplier_name}' not found.")
            payload_dict["supplier_id"] = supplier.id
        payload = ShipmentCreate(**payload_dict)
        if not db.get(Supplier, payload.supplier_id):
            raise ValueError(f"Supplier id {payload.supplier_id} does not exist.")
        if payload.purchase_order_id and not db.get(PurchaseOrder, payload.purchase_order_id):
            raise ValueError(f"Purchase order id {payload.purchase_order_id} does not exist.")
        return Shipment(**payload.model_dump())

    return await csv_import_service.import_csv(db, file, "shipment", build, current_user.email)
