from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Block(Base):
    """
    Blockchain Trust Module (module 9) ledger.

    A lightweight, permissioned, hash-chained ledger that mirrors the tamper-evidence
    guarantees of a private Hyperledger Fabric network: every record is appended,
    cryptographically linked to its predecessor via SHA-256, and any historical edit
    breaks the chain and is detectable by `verify_chain()`.
    """

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    # Stored as an exact ISO-8601 string (not a native DateTime) so the value used to
    # compute the hash at creation time is byte-for-byte identical to what is read back
    # from SQLite later -- a native DateTime column can lose timezone/precision on
    # round-trip and would make verify_chain() report false tampering.
    timestamp: Mapped[str] = mapped_column(String(40))

    event_type: Mapped[str] = mapped_column(String(80))  # e.g. supplier.created, shipment.delivered
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    performed_by: Mapped[str] = mapped_column(String(120), default="system")

    previous_hash: Mapped[str] = mapped_column(String(64))
    nonce: Mapped[int] = mapped_column(Integer, default=0)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class SmartContractRule(Base):
    """Registry of automated rules (module 10) executed whenever chain-relevant events occur."""

    __tablename__ = "smart_contract_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    trigger_event: Mapped[str] = mapped_column(String(80))
    condition_description: Mapped[str] = mapped_column(String(300))
    action_description: Mapped[str] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(default=True)
    times_triggered: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
