"""Shared "does this caller have any business touching this Purchase Order or Shipment"
check, used by the Messages and Documents routers (both attach to either entity type and
need identical supplier-scoping rules to the routers that own those entities)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.user import User

ENTITY_MODELS = {"purchase_order": PurchaseOrder, "shipment": Shipment}


def get_entity_or_404(db: Session, entity_type: str, entity_id: int):
    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type.")
    obj = db.get(model, entity_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type.replace('_', ' ').title()} not found.",
        )
    return obj


def assert_can_access_entity(db: Session, user: User, entity_type: str, entity_id: int):
    entity = get_entity_or_404(db, entity_type, entity_id)
    if user.role == UserRole.SUPPLIER and user.supplier_id != entity.supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return entity


def entity_label(entity) -> str:
    return getattr(entity, "po_number", None) or getattr(entity, "shipment_code", "")
