from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin
from app.models.enums import NotificationSeverity, UserRole
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services import blockchain_service, notification_service

router = APIRouter(prefix="/api/suppliers", tags=["Supplier Management"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    q: str | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.SUPPLIER:
        # External party: never the full supplier directory (that's competitor data) --
        # only the one record linked to their own portal account, if any.
        if current_user.supplier_id is None:
            return []
        return db.execute(select(Supplier).where(Supplier.id == current_user.supplier_id)).scalars().all()

    stmt = select(Supplier)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    if risk_level:
        stmt = stmt.where(Supplier.risk_level == risk_level)
    return db.execute(stmt.order_by(Supplier.id)).scalars().all()


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.SUPPLIER and current_user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return supplier


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    blockchain_service.add_block(
        db,
        event_type="supplier.created",
        payload={"entity_type": "supplier", "entity_id": supplier.id, "name": supplier.name},
        performed_by=current_user.email,
    )
    notification_service.create_notification(
        db,
        title="New Supplier Onboarded",
        message=f"Supplier '{supplier.name}' was added to the platform by {current_user.name}.",
        severity=NotificationSeverity.INFO,
        related_entity_type="supplier",
        related_entity_id=supplier.id,
        source="system",
    )
    return supplier


@router.put("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    blockchain_service.add_block(
        db,
        event_type="supplier.updated",
        payload={"entity_type": "supplier", "entity_id": supplier.id, "changes": payload.model_dump(exclude_unset=True)},
        performed_by=current_user.email,
    )
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    supplier_name = supplier.name
    db.delete(supplier)
    db.commit()
    blockchain_service.add_block(
        db,
        event_type="supplier.deleted",
        payload={"entity_type": "supplier", "entity_id": supplier_id, "name": supplier_name},
        performed_by=current_user.email,
    )
    return None
