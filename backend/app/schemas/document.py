from datetime import datetime

from pydantic import ConfigDict, BaseModel


class DocumentRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    filename: str
    content_type: str
    file_size: int
    sha256_hash: str
    uploaded_by_name: str
    block_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentVerifyResult(BaseModel):
    document_id: int
    is_verified: bool
    sha256_hash: str
    message: str
