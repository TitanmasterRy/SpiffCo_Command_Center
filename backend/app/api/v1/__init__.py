"""Version 1 REST API routers."""

from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.gamedata import router as gamedata_router
from app.api.v1.plans import router as plans_router
from app.api.v1.system import router as system_router
from app.api.v1.world import router as world_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(world_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(gamedata_router)

__all__ = ["api_v1_router"]
