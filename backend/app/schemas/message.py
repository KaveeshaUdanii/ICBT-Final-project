from datetime import datetime

from pydantic import ConfigDict, BaseModel, Field


class MessageCreate(BaseModel):
    entity_type: str = Field(pattern="^(purchase_order|shipment)$")
    entity_id: int
    body: str = Field(min_length=1, max_length=1000)


class MessageRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    sender_user_id: int
    sender_name: str
    sender_role: str
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
