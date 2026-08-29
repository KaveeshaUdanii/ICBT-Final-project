from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.enums import UserRole
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.auth import UserRead

router = APIRouter(prefix="/api/users", tags=["Authentication & User Management"])


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.id)).scalars().all()


@router.patch("/{user_id}/role", response_model=UserRead, dependencies=[Depends(require_admin)])
def update_role(user_id: int, role: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    try:
        user.role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserRead, dependencies=[Depends(require_admin)])
def toggle_active(user_id: int, is_active: bool, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/supplier", response_model=UserRead, dependencies=[Depends(require_admin)])
def link_supplier(user_id: int, supplier_id: int | None = None, db: Session = Depends(get_db)):
    """Links (or unlinks, with supplier_id omitted) a Supplier-portal account to one specific
    Supplier company record. This is the piece that was otherwise missing end-to-end: the public
    self-registration form lets someone create a login with role=Supplier, but that only ever
    creates the User row -- it can never know which Supplier company record to attach itself to.
    An Admin creates the actual Supplier record (Supplier Management > Add Supplier) and then
    performs the linkage here, which is what makes that account's scoped shipments/POs/dashboard
    actually show real data instead of "no supplier profile linked"."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.role != UserRole.SUPPLIER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Supplier-role accounts can be linked to a supplier record.",
        )
    if supplier_id is not None and not db.get(Supplier, supplier_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not exist.")
    user.supplier_id = supplier_id
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
