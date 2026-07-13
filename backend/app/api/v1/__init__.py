"""Version 1 REST API routers."""

from fastapi import APIRouter

from app.api.v1.advisor import router as advisor_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.blueprints import router as blueprints_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.gamedata import router as gamedata_router
from app.api.v1.logistics import router as logistics_router
from app.api.v1.offline import router as offline_router
from app.api.v1.plans import router as plans_router
from app.api.v1.power import router as power_router
from app.api.v1.production import router as production_router
from app.api.v1.system import router as system_router
from app.api.v1.world import router as world_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(world_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(gamedata_router)
api_v1_router.include_router(production_router)
api_v1_router.include_router(logistics_router)
api_v1_router.include_router(power_router)
api_v1_router.include_router(blueprints_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(advisor_router)
api_v1_router.include_router(offline_router)

__all__ = ["api_v1_router"]
