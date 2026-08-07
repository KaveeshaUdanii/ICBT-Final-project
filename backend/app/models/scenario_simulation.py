from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ScenarioType


class ScenarioSimulation(Base):
    """Scenario Simulation module (13): what-if analysis results."""

    __tablename__ = "scenario_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    scenario_type: Mapped[ScenarioType] = mapped_column(Enum(ScenarioType, native_enum=False, length=30))
    input_params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
