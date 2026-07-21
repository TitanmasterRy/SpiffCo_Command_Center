"""Admin cheat-panel endpoints. All require the ``use:admin-cheats`` permission."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.item_catalog import load_item_catalog
from app.api.deps import get_session, require_permission
from app.models.user import User
from app.schemas.admin import (
    AdminState,
    BridgeActions,
    CheatCatalog,
    CheatExecuteRequest,
    CheatExecuteResult,
    CheatLogEntry,
    PresetList,
    SpawnItemInfo,
)
from app.services.admin_cheats import AdminCheatService

router = APIRouter(prefix="/admin", tags=["admin"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

#: Every cheat endpoint requires the caller to hold ``use:admin-cheats``.
AdminUser = Annotated[User, Depends(require_permission("use:admin-cheats"))]


def _cheats(request: Request) -> AdminCheatService:
    service: AdminCheatService = request.app.state.admin_cheats
    return service


@router.get("/catalog", response_model=CheatCatalog)
async def catalog(request: Request, _: AdminUser) -> CheatCatalog:
    """Return the full cheat catalog and executor capability."""
    return _cheats(request).catalog()


@router.get("/state", response_model=AdminState)
async def state(request: Request, _: AdminUser) -> AdminState:
    """Return current toggle states."""
    return _cheats(request).state()


@router.get("/item-catalog", response_model=list[SpawnItemInfo])
async def item_catalog(_: AdminUser) -> list[SpawnItemInfo]:
    """Every giveable in-game item (for the spawn picker's search)."""
    return list(load_item_catalog())


@router.get("/bridge-actions", response_model=BridgeActions)
async def bridge_actions(request: Request, _: AdminUser) -> BridgeActions:
    """Which catalog actions the connected game bridge actually implements."""
    return await _cheats(request).bridge_actions()


@router.post("/execute", response_model=CheatExecuteResult)
async def execute(request: Request, body: CheatExecuteRequest,
                  user: AdminUser) -> CheatExecuteResult:
    """Run one cheat action."""
    return await _cheats(request).execute(body, user.username)


@router.get("/log", response_model=list[CheatLogEntry])
async def log(request: Request, _: AdminUser) -> list[CheatLogEntry]:
    """Return the admin command audit log (newest first)."""
    return _cheats(request).log()


@router.get("/presets/{kind}", response_model=PresetList)
async def get_presets(kind: str, request: Request, _: AdminUser,
                      session: SessionDep) -> PresetList:
    """Return saved presets of a kind (e.g. ``teleports``, ``inventories``)."""
    return await _cheats(request).get_presets(session, kind)


@router.put("/presets/{kind}", response_model=PresetList)
async def put_presets(kind: str, body: PresetList, request: Request, _: AdminUser,
                      session: SessionDep) -> PresetList:
    """Replace saved presets of a kind. The path kind wins over the body kind."""
    return await _cheats(request).put_presets(
        session, PresetList(kind=kind, items=body.items)
    )
