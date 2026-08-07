from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.schemas.auth import UserRead

router = APIRouter(prefix="/api/users", tags=["Authentication & User Management"])


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.id)).scalars().all()


@router.patch("/{user_id}/role", response_model=UserRead, dependencies=[Depends(require_admin)])
def update_role(user_id: int, role: str, db: Session = Depends(get_db)):
    from app.models.enums import UserRole

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
