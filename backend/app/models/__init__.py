"""SQLAlchemy ORM models.

Import every model module here so ``Base.metadata`` knows about all tables
before ``create_all`` runs.
"""

from app.models.app_setting import AppSetting
from app.models.base import Base
from app.models.history import PowerSample, ProductionSample
from app.models.map_marker import MapMarker
from app.models.plan import FactoryPlan, PlanVersion

__all__ = [
    "Base",
    "AppSetting",
    "PowerSample",
    "ProductionSample",
    "MapMarker",
    "FactoryPlan",
    "PlanVersion",
]
