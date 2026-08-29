from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_manager_or_admin
from app.models.enums import NotificationSeverity, UserRole
from app.models.risk_prediction import RiskPrediction
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate,
    SupplierExternalRead,
    SupplierProfileUpdate,
    SupplierRead,
    SupplierRiskHistoryEntry,
    SupplierUpdate,
)
from app.services import blockchain_service, csv_import_service, notification_service

router = APIRouter(prefix="/api/suppliers", tags=["Supplier Management"])


def _risk_level_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _to_read(supplier: Supplier, current_user: User) -> dict:
    # A Supplier-portal account never sees the AI Risk Engine's own classification of it --
    # see SupplierExternalRead's docstring for why that's excluded, not just hidden in the UI.
    # Returned as a plain dict (route declares response_model=None) rather than validated
    # against a Union[SupplierExternalRead, SupplierRead]: since SupplierExternalRead's fields
    # are a strict subset of SupplierRead's, FastAPI/Pydantic would happily validate *any*
    # supplier -- including an internal caller's -- against the narrower schema first and
    # silently strip the risk fields for everyone, not just the external caller.
    schema = SupplierExternalRead if current_user.role == UserRole.SUPPLIER else SupplierRead
    return schema.model_validate(supplier).model_dump(mode="json")


@router.get("", response_model=None)
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
        suppliers = db.execute(select(Supplier).where(Supplier.id == current_user.supplier_id)).scalars().all()
        return [_to_read(s, current_user) for s in suppliers]

    stmt = select(Supplier)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    if risk_level:
        stmt = stmt.where(Supplier.risk_level == risk_level)
    suppliers = db.execute(stmt.order_by(Supplier.id)).scalars().all()
    return [_to_read(s, current_user) for s in suppliers]


@router.get("/{supplier_id}", response_model=None)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.SUPPLIER and current_user.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return _to_read(supplier, current_user)


@router.patch("/me/profile", response_model=None)
def update_my_profile(
    payload: SupplierProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Self-service contact-info edit for a Supplier-portal account. A real vendor portal lets
    the supplier maintain their own contact details rather than filing a request with an
    Admin for a one-line email change."""
    if current_user.role != UserRole.SUPPLIER or current_user.supplier_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a linked Supplier account can use this endpoint.")

    supplier = db.get(Supplier, current_user.supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(supplier, field, value)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    if changes:
        blockchain_service.add_block(
            db,
            event_type="supplier.self_profile_updated",
            payload={"entity_type": "supplier", "entity_id": supplier.id, "changes": changes},
            performed_by=current_user.email,
        )
    return _to_read(supplier, current_user)


@router.get("/{supplier_id}/risk-history", response_model=list[SupplierRiskHistoryEntry])
def get_risk_history(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
):
    """Every past supplier.risk_scored run, so a manager can see whether a supplier's risk is
    trending up or down over time rather than only ever seeing the latest snapshot -- directly
    answers the "lack of a structured system to monitor reliability over time" gap."""
    if not db.get(Supplier, supplier_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    rows = db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.entity_type == "supplier", RiskPrediction.entity_id == supplier_id)
        .order_by(RiskPrediction.created_at.asc())
    ).scalars().all()
    return [
        SupplierRiskHistoryEntry(
            risk_score=r.prediction_value,
            risk_level=_risk_level_from_score(r.prediction_value),
            scored_at=r.created_at,
        )
        for r in rows
    ]


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


@router.post("/import-csv")
async def import_suppliers_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Bulk-imports suppliers from a CSV export -- the way most real ERP systems bring data in,
    rather than one row at a time through the form above."""
    allowed_fields = set(SupplierCreate.model_fields.keys())

    def build(row: dict):
        payload_dict = csv_import_service.row_payload(row, allowed_fields)
        payload = SupplierCreate(**payload_dict)
        return Supplier(**payload.model_dump())

    return await csv_import_service.import_csv(db, file, "supplier", build, current_user.email)
