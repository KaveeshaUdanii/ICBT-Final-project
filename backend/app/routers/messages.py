from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import NotificationSeverity, UserRole
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead
from app.services import notification_service
from app.services.entity_access import assert_can_access_entity, entity_label

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("", response_model=list[MessageRead])
def list_messages(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_can_access_entity(db, current_user, entity_type, entity_id)
    stmt = (
        select(Message)
        .where(Message.entity_type == entity_type, Message.entity_id == entity_id)
        .order_by(Message.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def create_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity = assert_can_access_entity(db, current_user, payload.entity_type, payload.entity_id)

    message = Message(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        sender_user_id=current_user.id,
        sender_name=current_user.name,
        sender_role=current_user.role.value,
        body=payload.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    label = entity_label(entity)
    title = f"New message on {label}"
    snippet = payload.body if len(payload.body) <= 140 else payload.body[:137] + "..."

    if current_user.role == UserRole.SUPPLIER:
        # Supplier posted -- notify internal staff (broadcast, same as other smart-contract
        # alerts staff already see in the bell).
        notification_service.create_notification(
            db,
            title=title,
            message=f"{current_user.name}: {snippet}",
            severity=NotificationSeverity.INFO,
            related_entity_type=payload.entity_type,
            related_entity_id=payload.entity_id,
            source="system",
        )
    else:
        # Staff posted -- notify that supplier's own portal account directly, never a
        # broadcast (a supplier must never see another supplier's notifications).
        supplier_user = db.execute(
            select(User).where(User.role == UserRole.SUPPLIER, User.supplier_id == entity.supplier_id)
        ).scalars().first()
        if supplier_user:
            notification_service.create_notification(
                db,
                title=title,
                message=f"{current_user.name}: {snippet}",
                severity=NotificationSeverity.INFO,
                user_id=supplier_user.id,
                related_entity_type=payload.entity_type,
                related_entity_id=payload.entity_id,
                source="system",
            )

    return message
