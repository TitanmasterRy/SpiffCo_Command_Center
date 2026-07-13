"""Offline-mode endpoints: upload/select a save file as the live data source."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.deps import get_settings
from app.config.settings import Settings
from app.errors import ValidationFailedError
from app.offline.manager import OfflineManager
from app.schemas.offline import OfflineStatus

router = APIRouter(prefix="/offline", tags=["offline"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _manager(request: Request) -> OfflineManager:
    manager: OfflineManager = request.app.state.offline
    return manager


@router.get("/status", response_model=OfflineStatus)
async def status(request: Request) -> OfflineStatus:
    """Report the active data source and, if a save is loaded, its summary."""
    return _manager(request).status()


@router.post("/save", response_model=OfflineStatus)
async def upload_save(
    request: Request,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="A Satisfactory .sav file")],
) -> OfflineStatus:
    """Parse an uploaded save and make it the live data source.

    Raises 422 if the file is empty, too large, or not a parseable save.
    """
    data = await file.read()
    if not data:
        raise ValidationFailedError("Uploaded file is empty")
    max_bytes = settings.save_max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValidationFailedError(
            f"Save file exceeds the {settings.save_max_upload_mb} MB limit",
            details={"size_bytes": len(data), "limit_bytes": max_bytes},
        )
    await _manager(request).load_save(data)
    return _manager(request).status()


@router.delete("/save", response_model=OfflineStatus)
async def clear_save(request: Request) -> OfflineStatus:
    """Unload the save and restore the base data source (simulation or FRM)."""
    await _manager(request).clear()
    return _manager(request).status()
