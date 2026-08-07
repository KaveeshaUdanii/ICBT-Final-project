from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_staff
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.ai import RecommendationRead

router = APIRouter(prefix="/api/recommendations", tags=["Recommendation Engine"])


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(
    include_dismissed: bool = False,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    stmt = select(Recommendation).order_by(Recommendation.id.desc())
    if not include_dismissed:
        stmt = stmt.where(Recommendation.is_dismissed.is_(False))
    if entity_type:
        stmt = stmt.where(Recommendation.entity_type == entity_type)
    return db.execute(stmt).scalars().all()


@router.post("/{recommendation_id}/dismiss", response_model=RecommendationRead)
def dismiss_recommendation(recommendation_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    rec = db.get(Recommendation, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    rec.is_dismissed = True
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
