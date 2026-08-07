from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_manager_or_admin
from app.models.blockchain import Block, SmartContractRule
from app.models.user import User
from app.schemas.blockchain import BlockRead, ChainVerificationResult, SmartContractRuleRead
from app.services import blockchain_service

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain Trust Module"])


@router.get("/blocks", response_model=list[BlockRead])
def list_blocks(
    limit: int = 100,
    event_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
):
    stmt = select(Block).order_by(Block.block_index.desc())
    if event_type:
        stmt = stmt.where(Block.event_type == event_type)
    return db.execute(stmt.limit(limit)).scalars().all()


@router.get("/blocks/{block_index}", response_model=BlockRead)
def get_block(block_index: int, db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    block = db.execute(select(Block).where(Block.block_index == block_index)).scalars().first()
    if not block:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")
    return block


@router.get("/verify", response_model=ChainVerificationResult)
def verify_chain(db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    return blockchain_service.verify_chain(db)


@router.get("/rules", response_model=list[SmartContractRuleRead])
def list_rules(db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    return db.execute(select(SmartContractRule).order_by(SmartContractRule.id)).scalars().all()
