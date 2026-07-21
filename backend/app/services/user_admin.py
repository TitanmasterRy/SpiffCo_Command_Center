"""Business logic for admin account management (approve/update/remove users)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.user import STATUS_ACTIVE, STATUS_DISABLED, User
from app.schemas.auth import ApproveRequest, UpdateUserRequest, UserSummary
from app.services.permissions import preset_permissions, sanitize_permissions

_VALID_STATUS = {STATUS_ACTIVE, STATUS_DISABLED, "pending"}


def to_summary(user: User) -> UserSummary:
    """Project a ``User`` row to its public admin-table representation."""
    return UserSummary(
        id=user.id,
        username=user.username,
        status=user.status,
        role=user.role,
        permissions=preset_permissions("admin") if user.is_superuser else user.permissions,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
    )


class UserAdminService:
    """Approve, update, and remove user accounts."""

    async def list_users(self, session: AsyncSession) -> list[UserSummary]:
        """All users, newest first."""
        rows = await session.scalars(select(User).order_by(User.created_at.desc()))
        return [to_summary(u) for u in rows]

    async def _get(self, session: AsyncSession, user_id: int) -> User:
        user = await session.get(User, user_id)
        if user is None:
            raise NotFoundError(f"No user with id {user_id}")
        return user

    async def approve(
        self, session: AsyncSession, user_id: int, body: ApproveRequest
    ) -> UserSummary:
        """Activate a pending account with a role and (optional) permission set."""
        user = await self._get(session, user_id)
        perms = body.permissions if body.permissions is not None else preset_permissions(body.role)
        user.status = STATUS_ACTIVE
        user.role = body.role
        user.permissions = sanitize_permissions(perms)
        await session.commit()
        await session.refresh(user)
        return to_summary(user)

    async def update(
        self, session: AsyncSession, user_id: int, body: UpdateUserRequest
    ) -> UserSummary:
        """Patch a user's role, permissions, and/or status."""
        user = await self._get(session, user_id)
        if user.is_superuser and (body.status is not None and body.status != STATUS_ACTIVE):
            raise ValidationFailedError("The owner account cannot be disabled")
        if body.role is not None:
            user.role = body.role
        if body.permissions is not None and not user.is_superuser:
            user.permissions = sanitize_permissions(body.permissions)
        if body.status is not None:
            if body.status not in _VALID_STATUS:
                raise ValidationFailedError(f"Invalid status: {body.status}")
            user.status = body.status
        await session.commit()
        await session.refresh(user)
        return to_summary(user)

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        """Remove (reject) an account. The owner account is protected."""
        user = await self._get(session, user_id)
        if user.is_superuser:
            raise ConflictError("The owner account cannot be deleted")
        await session.delete(user)
        await session.commit()
