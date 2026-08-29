from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentVerifyResult
from app.services import document_service
from app.services.entity_access import assert_can_access_entity

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_can_access_entity(db, current_user, entity_type, entity_id)
    stmt = (
        select(Document)
        .where(Document.entity_type == entity_type, Document.entity_id == entity_id)
        .order_by(Document.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    entity_type: str,
    entity_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_can_access_entity(db, current_user, entity_type, entity_id)

    content = await file.read()
    if len(content) > document_service.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds the {document_service.MAX_UPLOAD_SIZE // (1024 * 1024)} MB upload limit.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")

    return document_service.save_document(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        uploaded_by_user_id=current_user.id,
        uploaded_by_name=current_user.name,
    )


@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    assert_can_access_entity(db, current_user, document.entity_type, document.entity_id)
    return FileResponse(document.storage_path, filename=document.filename, media_type=document.content_type)


@router.get("/{document_id}/verify", response_model=DocumentVerifyResult)
def verify_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    assert_can_access_entity(db, current_user, document.entity_type, document.entity_id)

    is_verified = document_service.verify_document(document)
    message = (
        "File on disk matches the hash anchored on the blockchain ledger -- provenance confirmed."
        if is_verified
        else "File content does not match the anchored hash, or the file is missing. Provenance could not be verified."
    )
    return DocumentVerifyResult(
        document_id=document.id, is_verified=is_verified, sha256_hash=document.sha256_hash, message=message
    )
