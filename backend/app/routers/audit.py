from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_manager_or_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.blockchain import AuditLogRead

router = APIRouter(prefix="/api/audit-logs", tags=["Blockchain Audit Trail"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    return db.execute(stmt.limit(limit)).scalars().all()
