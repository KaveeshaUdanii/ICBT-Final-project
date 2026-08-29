from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import chatbot
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import UserRole
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.user import User

router = APIRouter(prefix="/api/chatbot", tags=["Supplier Portal Chatbot"])


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ChatReply(BaseModel):
    reply: str
    intent: str
    confidence: float


def _require_supplier(current_user: User) -> None:
    if current_user.role != UserRole.SUPPLIER or current_user.supplier_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The chatbot is only available to linked Supplier-portal accounts.",
        )


def _answer_shipment_status(db: Session, supplier_id: int, code: str | None) -> str:
    if code:
        shipment = db.execute(
            select(Shipment).where(Shipment.supplier_id == supplier_id, Shipment.shipment_code.ilike(code))
        ).scalars().first()
        if not shipment:
            return f"I couldn't find a shipment '{code}' linked to your account. Double-check the code?"
        parts = [f"Shipment '{shipment.shipment_code}' is currently **{shipment.status.value.replace('_', ' ')}**."]
        if shipment.tracking_number:
            parts.append(f"Tracking: {shipment.tracking_number} ({shipment.carrier or 'carrier not set'}).")
        parts.append(f"Expected delivery: {shipment.expected_delivery_date}.")
        if shipment.actual_delivery_date:
            parts.append(f"Actual delivery: {shipment.actual_delivery_date}.")
        return " ".join(parts)

    shipments = db.execute(
        select(Shipment).where(Shipment.supplier_id == supplier_id).order_by(Shipment.expected_delivery_date.asc())
    ).scalars().all()
    open_ones = [s for s in shipments if s.status.value in ("pending", "in_transit", "delayed")][:5]
    if not open_ones:
        return "You have no shipments currently in progress."
    lines = [f"- {s.shipment_code}: {s.status.value.replace('_', ' ')}, due {s.expected_delivery_date}" for s in open_ones]
    return "Here are your open shipments:\n" + "\n".join(lines)


def _answer_po_status(db: Session, supplier_id: int, code: str | None) -> str:
    if code:
        po = db.execute(
            select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id, PurchaseOrder.po_number.ilike(code))
        ).scalars().first()
        if not po:
            return f"I couldn't find a purchase order '{code}' linked to your account. Double-check the code?"
        reply = f"PO '{po.po_number}' is currently **{po.status.value.replace('_', ' ')}** (your response: {po.supplier_response})."
        if po.penalty_exposure:
            reply += f" Note: it currently carries a computed SLA penalty exposure of ${po.penalty_exposure:,.2f}."
        return reply

    pos = db.execute(
        select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id).order_by(PurchaseOrder.order_date.desc())
    ).scalars().all()[:5]
    if not pos:
        return "You have no purchase orders on record."
    lines = [f"- {po.po_number}: {po.status.value.replace('_', ' ')} (response: {po.supplier_response})" for po in pos]
    return "Here are your most recent purchase orders:\n" + "\n".join(lines)


def _answer_pending_pos(db: Session, supplier_id: int) -> str:
    pos = db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.supplier_response == "pending",
            PurchaseOrder.status != "rejected",
        )
    ).scalars().all()
    if not pos:
        return "You have no purchase orders waiting for your response right now."
    lines = [f"- {po.po_number}: due {po.expected_delivery_date}, value ${po.total_value:,.2f}" for po in pos]
    return f"You have {len(pos)} purchase order(s) awaiting your response:\n" + "\n".join(lines)


def _answer_performance(db: Session, supplier_id: int) -> str:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        return "I couldn't find your supplier record."
    return (
        f"Your on-time delivery rate is {supplier.on_time_delivery_rate * 100:.0f}%, "
        f"defect rate {supplier.defect_rate * 100:.0f}%, cancellation rate {supplier.cancellation_rate * 100:.0f}%, "
        f"average lead time {supplier.avg_lead_time_days:.0f} days. "
        f"You can see the month-by-month trend on your Dashboard."
    )


HELP_MESSAGE = (
    "I can help with:\n"
    "- Shipment status (e.g. \"where is SHP-001-02\")\n"
    "- Purchase order status (e.g. \"status of PO-018-01\")\n"
    "- Purchase orders waiting for your response\n"
    "- Your own delivery performance\n"
    "Ask me anything along those lines."
)


@router.post("/message", response_model=ChatReply)
def send_message(payload: ChatMessage, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_supplier(current_user)

    if not chatbot.is_trained():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The chatbot's intent model is not yet trained.")

    intent, confidence = chatbot.predict_intent(payload.message)
    code = chatbot.extract_code(payload.message)
    supplier_id = current_user.supplier_id

    if intent == "greeting":
        reply = "Hello! I'm your Supplier Portal assistant. Ask me about a shipment, a purchase order, or your performance."
    elif intent == "shipment_status":
        reply = _answer_shipment_status(db, supplier_id, code)
    elif intent == "po_status":
        reply = _answer_po_status(db, supplier_id, code)
    elif intent == "pending_pos":
        reply = _answer_pending_pos(db, supplier_id)
    elif intent == "performance":
        reply = _answer_performance(db, supplier_id)
    elif intent == "help":
        reply = HELP_MESSAGE
    elif intent == "thanks":
        reply = "You're welcome! Let me know if there's anything else."
    else:
        reply = chatbot.FALLBACK_MESSAGE

    return ChatReply(reply=reply, intent=intent, confidence=round(confidence, 3))
