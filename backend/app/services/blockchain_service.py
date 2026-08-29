"""
Blockchain Trust Module (module 9) + Blockchain Audit Trail (module 15).

Implements a lightweight, permissioned, hash-chained ledger that provides the same
tamper-evidence and traceability guarantees the proposal assigns to Hyperledger Fabric,
without requiring a Docker/Go chaincode network. Every supplier, shipment, purchase-order
and AI-prediction event is appended as an immutable block. `verify_chain` recomputes every
hash and confirms `previous_hash` linkage, so any historical tampering with the database
is instantly detectable -- the same integrity property a permissioned blockchain provides.
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.blockchain import Block

MAX_APPEND_ATTEMPTS = 8

GENESIS_PREVIOUS_HASH = "0" * 64


def _compute_hash(block_index: int, timestamp: str, event_type: str, payload: dict, performed_by: str, previous_hash: str, nonce: int) -> str:
    block_string = json.dumps(
        {
            "block_index": block_index,
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload,
            "performed_by": performed_by,
            "previous_hash": previous_hash,
            "nonce": nonce,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(block_string.encode("utf-8")).hexdigest()


def get_latest_block(db: Session) -> Block | None:
    return db.execute(select(Block).order_by(Block.block_index.desc())).scalars().first()


def add_block(db: Session, event_type: str, payload: dict, performed_by: str = "system") -> Block:
    """Appends a new immutable block to the chain and mirrors it into the audit trail.

    block_index is assigned by reading the current latest block and adding one -- under
    concurrent requests (e.g. the Admin dashboard's "Refresh All AI Models" button, which
    fires several bulk-scoring endpoints in parallel, each appending many blocks in a loop)
    two requests can both read the same "latest" block before either commits, then race to
    insert the same next index and hit the table's UNIQUE constraint. Rather than take a
    DB-specific row lock (Postgres supports SELECT ... FOR UPDATE; SQLite, still supported
    here as a fallback, does not), retry with a fresh read on conflict -- portable to both
    and correct as long as attempts stay bounded.
    """
    for attempt in range(MAX_APPEND_ATTEMPTS):
        latest = get_latest_block(db)
        block_index = (latest.block_index + 1) if latest else 0
        previous_hash = latest.hash if latest else GENESIS_PREVIOUS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()
        nonce = 0

        block_hash = _compute_hash(block_index, timestamp, event_type, payload, performed_by, previous_hash, nonce)

        block = Block(
            block_index=block_index,
            timestamp=timestamp,
            event_type=event_type,
            payload=payload,
            performed_by=performed_by,
            previous_hash=previous_hash,
            nonce=nonce,
            hash=block_hash,
        )
        db.add(block)
        try:
            db.flush()  # populate block.id without committing
            break
        except IntegrityError:
            db.rollback()
            if attempt == MAX_APPEND_ATTEMPTS - 1:
                raise

    audit = AuditLog(
        action=event_type,
        entity_type=payload.get("entity_type", "unknown"),
        entity_id=payload.get("entity_id"),
        performed_by=performed_by,
        details=payload,
        block_id=block.id,
    )
    db.add(audit)
    db.commit()
    db.refresh(block)
    return block


def verify_chain(db: Session) -> dict:
    blocks = db.execute(select(Block).order_by(Block.block_index.asc())).scalars().all()
    if not blocks:
        return {"is_valid": True, "total_blocks": 0, "broken_at_index": None, "message": "Ledger is empty."}

    expected_previous = GENESIS_PREVIOUS_HASH
    for block in blocks:
        recomputed = _compute_hash(
            block.block_index,
            block.timestamp,
            block.event_type,
            block.payload,
            block.performed_by,
            block.previous_hash,
            block.nonce,
        )
        if block.previous_hash != expected_previous or recomputed != block.hash:
            return {
                "is_valid": False,
                "total_blocks": len(blocks),
                "broken_at_index": block.block_index,
                "message": f"Chain integrity violated at block #{block.block_index}. "
                f"Stored hash does not match recomputed hash or previous_hash link is broken.",
            }
        expected_previous = block.hash

    return {
        "is_valid": True,
        "total_blocks": len(blocks),
        "broken_at_index": None,
        "message": "Chain is intact. All blocks are cryptographically linked and unmodified.",
    }
