from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin, require_staff
from app.models.enums import UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate
from app.services import blockchain_service

router = APIRouter(prefix="/api/shipments", tags=["Shipment Management"])


def _to_read(shipment: Shipment) -> ShipmentRead:
    data = ShipmentRead.model_validate(shipment).model_dump()
    data["actual_delay_days"] = shipment.actual_delay_days
    return ShipmentRead(**data)


def _assert_supplier_can_view(user: User, supplier_id: int) -> None:
    """A supplier-portal account may only ever see its own shipments -- this is an
    external party, so cross-supplier visibility would leak competitor information."""
    if user.role == UserRole.SUPPLIER and user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")


@router.get("", response_model=list[ShipmentRead])
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
    return [_to_read(s) for s in shipments]


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")
    _assert_supplier_can_view(current_user, shipment.supplier_id)
    return _to_read(shipment)


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
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

    shipment = Shipment(**payload.model_dump())
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    blockchain_service.add_block(
        db,
        event_type="shipment.created",
        payload={"entity_type": "shipment", "entity_id": shipment.id, "shipment_code": shipment.shipment_code},
        performed_by=current_user.email,
    )
    return _to_read(shipment)


@router.put("/{shipment_id}", response_model=ShipmentRead)
def update_shipment(
    shipment_id: int,
    payload: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

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
    return _to_read(shipment)


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
