from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_not_supplier, require_staff
from app.models.raw_material import RawMaterial
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.raw_material import RawMaterialCreate, RawMaterialRead, RawMaterialUpdate
from app.services import recommendation_service, smart_contract_service

router = APIRouter(prefix="/api/raw-materials", tags=["Raw Material Management"])


@router.get("", response_model=list[RawMaterialRead])
def list_materials(
    needs_reorder: bool | None = None,
    supplier_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_not_supplier),
):
    stmt = select(RawMaterial)
    if supplier_id:
        stmt = stmt.where(RawMaterial.supplier_id == supplier_id)
    materials = db.execute(stmt.order_by(RawMaterial.id)).scalars().all()
    if needs_reorder is not None:
        materials = [m for m in materials if m.needs_reorder == needs_reorder]
    return materials


@router.get("/{material_id}", response_model=RawMaterialRead)
def get_material(material_id: int, db: Session = Depends(get_db), _: User = Depends(require_not_supplier)):
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found.")
    return material


@router.post("", response_model=RawMaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: RawMaterialCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not exist.")

    material = RawMaterial(**payload.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)

    smart_contract_service.evaluate_raw_material_stock(db, material)
    recommendation_service.recommend_reorder(db, material)
    return material


@router.put("/{material_id}", response_model=RawMaterialRead)
def update_material(
    material_id: int,
    payload: RawMaterialUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, field, value)
    db.add(material)
    db.commit()
    db.refresh(material)

    smart_contract_service.evaluate_raw_material_stock(db, material)
    recommendation_service.recommend_reorder(db, material)
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    material = db.get(RawMaterial, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found.")
    db.delete(material)
    db.commit()
    return None
