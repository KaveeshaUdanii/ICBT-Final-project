from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin
from app.models.enums import PurchaseOrderStatus, UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.raw_material import RawMaterial
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderRead, PurchaseOrderUpdate
from app.services import blockchain_service, smart_contract_service

router = APIRouter(prefix="/api/purchase-orders", tags=["Purchase Order Management"])


def _assert_supplier_can_view(user: User, supplier_id: int) -> None:
    if user.role == UserRole.SUPPLIER and user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")


@router.get("", response_model=list[PurchaseOrderRead])
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

    return db.execute(stmt.order_by(PurchaseOrder.id.desc())).scalars().all()


@router.get("/{po_id}", response_model=PurchaseOrderRead)
def get_purchase_order(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    _assert_supplier_can_view(current_user, po.supplier_id)
    return po


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
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

    po = PurchaseOrder(**payload.model_dump(), status=PurchaseOrderStatus.PENDING_APPROVAL)
    db.add(po)
    db.commit()
    db.refresh(po)

    smart_contract_service.evaluate_purchase_order(db, po, supplier)
    db.refresh(po)
    return po


@router.post("/{po_id}/approve", response_model=PurchaseOrderRead, dependencies=[Depends(require_manager_or_admin)])
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
    return po


@router.post("/{po_id}/reject", response_model=PurchaseOrderRead, dependencies=[Depends(require_manager_or_admin)])
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
    return po


@router.put("/{po_id}", response_model=PurchaseOrderRead)
def update_purchase_order(
    po_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(po, field, value)
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(po_id: int, db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    db.delete(po)
    db.commit()
    return None
