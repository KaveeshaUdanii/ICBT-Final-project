from datetime import datetime

from pydantic import ConfigDict, BaseModel

from app.models.enums import ScenarioType


class ScenarioRequest(BaseModel):
    name: str
    scenario_type: ScenarioType
    input_params: dict


class ScenarioResult(BaseModel):
    id: int
    name: str
    scenario_type: ScenarioType
    input_params: dict
    result: dict
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
