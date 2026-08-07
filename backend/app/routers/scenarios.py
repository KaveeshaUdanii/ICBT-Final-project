from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_manager_or_admin
from app.models.scenario_simulation import ScenarioSimulation
from app.models.user import User
from app.schemas.scenario import ScenarioRequest, ScenarioResult
from app.services import scenario_service

router = APIRouter(prefix="/api/scenarios", tags=["Scenario Simulation"])


@router.post("/simulate", response_model=ScenarioResult)
def simulate(payload: ScenarioRequest, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_admin)):
    result = scenario_service.run_scenario(db, payload.scenario_type, payload.input_params)

    record = ScenarioSimulation(
        name=payload.name,
        scenario_type=payload.scenario_type,
        input_params=payload.input_params,
        result=result,
        created_by=current_user.email,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ScenarioResult])
def list_scenarios(limit: int = 50, db: Session = Depends(get_db), _: User = Depends(require_manager_or_admin)):
    return db.execute(select(ScenarioSimulation).order_by(ScenarioSimulation.id.desc()).limit(limit)).scalars().all()
