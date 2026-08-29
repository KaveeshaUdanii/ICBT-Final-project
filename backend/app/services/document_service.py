"""
Document hash anchoring (Blockchain Trust Module enhancement).

A supplier or internal staff member can attach a file (compliance certificate, spec sheet,
invoice) to a Purchase Order or Shipment. The file's SHA-256 hash is anchored on the
blockchain ledger at upload time via the same `blockchain_service.add_block` every other
event in this system goes through -- so if the physical/paper document is later disputed,
its digital counterpart's provenance (who uploaded it, when, and its exact content hash) is
independently verifiable against an immutable record, not just a filesystem timestamp.

Files are stored on local disk under UPLOADS_DIR -- a real deployment would use object
storage (S3 etc.), but the hash-anchoring mechanism itself, which is the actual academic
content here, is identical either way.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.models.document import Document
from app.services import blockchain_service

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def save_document(
    db: Session,
    entity_type: str,
    entity_id: int,
    filename: str,
    content_type: str,
    content: bytes,
    uploaded_by_user_id: int,
    uploaded_by_name: str,
) -> Document:
    sha256_hash = hashlib.sha256(content).hexdigest()
    safe_name = Path(filename).name  # strip any path components a malicious client might send
    storage_filename = f"{uuid.uuid4().hex}_{safe_name}"
    storage_path = UPLOADS_DIR / storage_filename
    storage_path.write_bytes(content)

    block = blockchain_service.add_block(
        db,
        event_type="document.uploaded",
        payload={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "filename": safe_name,
            "sha256_hash": sha256_hash,
            "file_size": len(content),
        },
        performed_by=uploaded_by_name,
    )

    document = Document(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=safe_name,
        content_type=content_type or "application/octet-stream",
        file_size=len(content),
        sha256_hash=sha256_hash,
        storage_path=str(storage_path),
        uploaded_by_user_id=uploaded_by_user_id,
        uploaded_by_name=uploaded_by_name,
        block_id=block.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def verify_document(document: Document) -> bool:
    """Recomputes the stored file's hash and compares it to the anchored value -- confirms the
    file on disk is byte-for-byte what was originally uploaded and anchored on-chain."""
    path = Path(document.storage_path)
    if not path.exists():
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == document.sha256_hash
