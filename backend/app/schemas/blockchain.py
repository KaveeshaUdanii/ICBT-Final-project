from datetime import datetime

from pydantic import ConfigDict, BaseModel


class BlockRead(BaseModel):
    id: int
    block_index: int
    timestamp: str
    event_type: str
    payload: dict
    performed_by: str
    previous_hash: str
    nonce: int
    hash: str

    model_config = ConfigDict(from_attributes=True)


class ChainVerificationResult(BaseModel):
    is_valid: bool
    total_blocks: int
    broken_at_index: int | None = None
    message: str


class SmartContractRuleRead(BaseModel):
    id: int
    name: str
    trigger_event: str
    condition_description: str
    action_description: str
    is_active: bool
    times_triggered: int
    last_triggered_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AuditLogRead(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int | None
    performed_by: str
    details: dict
    block_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
