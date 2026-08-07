from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if token is None:
        raise CREDENTIALS_EXCEPTION
    payload = decode_access_token(token)
    if payload is None:
        raise CREDENTIALS_EXCEPTION
    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_EXCEPTION
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION
    return user


def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to perform this action.",
            )
        return user

    return dependency


def require_not_supplier(user: User = Depends(get_current_user)) -> User:
    """Any internal-staff role (admin, supply chain manager, warehouse manager) -- blocks
    the external Supplier role from endpoints that expose cross-supplier / internal data."""
    if user.role == UserRole.SUPPLIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier accounts do not have access to this resource.",
        )
    return user


require_admin = require_roles(UserRole.ADMIN)
require_manager_or_admin = require_roles(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER)
# Any internal employee -- the day-to-day operational roles that touch inventory,
# receiving, and delay/stockout predictions. Excludes the external Supplier role.
require_staff = require_roles(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER, UserRole.WAREHOUSE_MANAGER)
