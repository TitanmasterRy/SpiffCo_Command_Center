"""Admin account-management endpoints (require the ``manage:users`` permission)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_permission
from app.schemas.auth import ApproveRequest, UpdateUserRequest, UserSummary
from app.services.user_admin import UserAdminService

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_permission("manage:users"))],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
_service = UserAdminService()


@router.get("", response_model=list[UserSummary])
async def list_users(session: SessionDep) -> list[UserSummary]:
    """List every account (pending and active), newest first."""
    return await _service.list_users(session)


@router.post("/{user_id}/approve", response_model=UserSummary)
async def approve_user(
    user_id: int, body: ApproveRequest, session: SessionDep
) -> UserSummary:
    """Approve a pending account, granting a role and permissions."""
    return await _service.approve(session, user_id, body)


@router.patch("/{user_id}", response_model=UserSummary)
async def update_user(
    user_id: int, body: UpdateUserRequest, session: SessionDep
) -> UserSummary:
    """Change a user's role, permissions, or status (enable/disable)."""
    return await _service.update(session, user_id, body)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, session: SessionDep) -> None:
    """Delete/reject an account."""
    await _service.delete(session, user_id)
