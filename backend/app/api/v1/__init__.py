"""Version 1 REST API routers.

Routing has two tiers: *open* routers (health check + authentication) are
reachable without a session; every *protected* router requires an active user
(:func:`app.api.deps.get_current_user`). When ``SPIFFCO_AUTH_ENABLED`` is false
that dependency resolves to a local all-access superuser, so the protected tier
behaves exactly as before login was introduced.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.admin import router as admin_router
from app.api.v1.advisor import router as advisor_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.blueprints import router as blueprints_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.gamedata import router as gamedata_router
from app.api.v1.logistics import router as logistics_router
from app.api.v1.offline import router as offline_router
from app.api.v1.plans import router as plans_router
from app.api.v1.power import router as power_router
from app.api.v1.production import router as production_router
from app.api.v1.system import router as system_router
from app.api.v1.users import router as users_router
from app.api.v1.world import router as world_router

api_v1_router = APIRouter(prefix="/api/v1")

# Open tier: no session required.
api_v1_router.include_router(system_router)
api_v1_router.include_router(auth_router)

# Protected tier: any active user. Routers that gate privileged actions
# (admin cheats, user management) add their own finer permission checks.
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(dashboard_router)
protected.include_router(world_router)
protected.include_router(plans_router)
protected.include_router(gamedata_router)
protected.include_router(production_router)
protected.include_router(logistics_router)
protected.include_router(power_router)
protected.include_router(blueprints_router)
protected.include_router(analytics_router)
protected.include_router(advisor_router)
protected.include_router(offline_router)
protected.include_router(admin_router)
protected.include_router(users_router)
api_v1_router.include_router(protected)

__all__ = ["api_v1_router"]
