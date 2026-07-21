"""Admin cheat catalog access, dispatch, toggle state, and audit log.

Dispatch is pluggable: when ``SPIFFCO_ADMIN_COMMAND_URL`` points at a game-side
command endpoint (a companion mod / dedicated-server bridge that accepts
``POST {action, params, enabled}``), actions execute for real. Otherwise the
simulated executor acknowledges them locally — the panel stays fully usable and
every action is logged, but nothing reaches a game. FRM itself is read-only
telemetry and cannot execute commands (see docs/KNOWN_LIMITATIONS.md).
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.catalog import build_catalog
from app.config.settings import Settings
from app.errors import NotFoundError, UpstreamUnavailableError, ValidationFailedError
from app.models.app_setting import AppSetting
from app.schemas.admin import (
    AdminState,
    BridgeActions,
    CheatAction,
    CheatCatalog,
    CheatExecuteRequest,
    CheatExecuteResult,
    CheatLogEntry,
    PresetList,
)
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)

_LOG_LIMIT = 200
_PRESET_KEY_PREFIX = "admin.presets."


class CheatExecutor(Protocol):
    """Sends one admin action to whatever can actually perform it."""

    name: str

    async def execute(self, action_id: str, params: dict[str, Any],
                      enabled: bool | None) -> dict[str, Any]:
        """Perform the action; return any response payload from the executor."""
        ...

    async def supported_actions(self) -> list[str] | None:
        """Action ids the executor can actually perform, or None if unknown."""
        ...

    async def aclose(self) -> None:
        """Release resources."""
        ...


class SimulatedExecutor:
    """Acknowledges actions locally when no game command endpoint is configured."""

    name = "simulated"

    async def execute(self, action_id: str, params: dict[str, Any],
                      enabled: bool | None) -> dict[str, Any]:
        return {"simulated": True}

    async def supported_actions(self) -> list[str] | None:
        # Simulation accepts everything, so nothing is disabled in the panel.
        return None

    async def aclose(self) -> None:
        return None


class CommandEndpointExecutor:
    """POSTs actions to a game-side command endpoint (companion mod bridge)."""

    name = "command_endpoint"

    def __init__(self, base_url: str, *, token: str = "", timeout: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        headers = {"X-SpiffCo-Token": token} if token else {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport,
            headers=headers,
        )

    async def execute(self, action_id: str, params: dict[str, Any],
                      enabled: bool | None) -> dict[str, Any]:
        body: dict[str, Any] = {"action": action_id, "params": params}
        if enabled is not None:
            body["enabled"] = enabled
        try:
            response = await self._client.post("/execute", json=body)
            response.raise_for_status()
            data = response.json() if response.content else {}
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamUnavailableError(
                f"Game command endpoint rejected {action_id!r}: {exc}",
                details={"action_id": action_id},
            ) from exc
        return data if isinstance(data, dict) else {"response": data}

    async def supported_actions(self) -> list[str] | None:
        """Ask the bridge (GET /health) which action ids it implements.

        Returns None if the bridge is unreachable — the panel then leaves every
        action enabled rather than hiding the whole catalog on a transient blip.
        """
        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        actions = data.get("actions") if isinstance(data, dict) else None
        return actions if isinstance(actions, list) else None

    async def aclose(self) -> None:
        await self._client.aclose()


class AdminCheatService:
    """Business logic for the admin panel: catalog, execution, state, log."""

    def __init__(self, settings: Settings, bus: EventBus,
                 executor: CheatExecutor | None = None) -> None:
        self._bus = bus
        self._categories = build_catalog()
        self._actions: dict[str, CheatAction] = {
            action.id: action
            for category in self._categories
            for section in category.sections
            for action in section.actions
        }
        self._toggles: dict[str, bool] = {}
        self._log: deque[CheatLogEntry] = deque(maxlen=_LOG_LIMIT)
        if executor is not None:
            self._executor: CheatExecutor = executor
        elif settings.admin_command_url:
            self._executor = CommandEndpointExecutor(
                settings.admin_command_url, token=settings.admin_command_token
            )
        else:
            self._executor = SimulatedExecutor()

    async def aclose(self) -> None:
        """Release the executor's resources."""
        await self._executor.aclose()

    def catalog(self) -> CheatCatalog:
        """Return the full action tree plus executor capability info."""
        if self._executor.name == "command_endpoint":
            hint = "Commands are sent to the configured game command endpoint."
        else:
            hint = (
                "No game command endpoint configured (SPIFFCO_ADMIN_COMMAND_URL) — "
                "actions are acknowledged and logged locally only. FRM telemetry "
                "is read-only and cannot execute in-game commands."
            )
        return CheatCatalog(
            categories=self._categories,
            executor=self._executor.name,
            executor_hint=hint,
        )

    async def bridge_actions(self) -> BridgeActions:
        """Report which catalog actions the game bridge actually implements.

        ``supported=None`` means "don't disable anything" (simulated mode or the
        bridge is unreachable); otherwise it is the exact set the panel enables.
        """
        return BridgeActions(
            executor=self._executor.name,
            supported=await self._executor.supported_actions(),
        )

    def state(self) -> AdminState:
        """Return the current toggle states."""
        return AdminState(toggles=dict(self._toggles))

    def log(self) -> list[CheatLogEntry]:
        """Return the audit log, newest first."""
        return list(reversed(self._log))

    async def execute(self, request: CheatExecuteRequest, username: str) -> CheatExecuteResult:
        """Dispatch one action, updating toggle state and the audit log.

        Raises:
            NotFoundError: unknown action id.
            ValidationFailedError: a required parameter is missing.
            UpstreamUnavailableError: the command endpoint refused the action.
        """
        action = self._actions.get(request.action_id)
        if action is None:
            raise NotFoundError(f"Unknown admin action {request.action_id!r}")

        missing = [
            p.name for p in action.params
            if p.default is None and request.params.get(p.name) in (None, "")
        ]
        if action.control == "button" and missing:
            raise ValidationFailedError(
                f"Missing parameters for {action.id!r}: {', '.join(missing)}",
                details={"missing": missing},
            )

        enabled: bool | None = None
        if action.control == "toggle":
            enabled = not self._toggles.get(action.id, False)

        try:
            response = await self._executor.execute(action.id, request.params, enabled)
        except UpstreamUnavailableError:
            self._append_log(username, action.id, request.params, "failed")
            raise

        if enabled is not None:
            self._toggles[action.id] = enabled

        status = "executed" if self._executor.name == "command_endpoint" else "simulated"
        self._append_log(username, action.id, request.params, status)
        self._bus.publish(
            "admin.cheat",
            {"action_id": action.id, "username": username, "status": status,
             "enabled": enabled},
        )

        if enabled is None:
            detail = f"{action.label}: {status}"
        else:
            detail = f"{action.label}: {'enabled' if enabled else 'disabled'} ({status})"
        return CheatExecuteResult(
            action_id=action.id,
            status=status,
            detail=detail,
            toggles=dict(self._toggles),
            response=response,
        )

    def _append_log(self, username: str, action_id: str, params: dict[str, Any],
                    status: str) -> None:
        self._log.append(CheatLogEntry(
            timestamp=datetime.now(UTC),
            username=username,
            action_id=action_id,
            params=params,
            status=status,
        ))

    # -- Presets (saved teleport locations, inventory presets, ...) ----------

    @staticmethod
    def _preset_key(kind: str) -> str:
        if not kind.replace("_", "").replace("-", "").isalnum() or len(kind) > 64:
            raise ValidationFailedError(f"Invalid preset kind {kind!r}")
        return f"{_PRESET_KEY_PREFIX}{kind}"

    async def get_presets(self, session: AsyncSession, kind: str) -> PresetList:
        """Return the saved presets of *kind* (empty list if none saved yet)."""
        row = await session.get(AppSetting, self._preset_key(kind))
        items = json.loads(row.value) if row is not None else []
        return PresetList(kind=kind, items=items)

    async def put_presets(self, session: AsyncSession, presets: PresetList) -> PresetList:
        """Replace the saved presets of a kind (stored in app_settings as JSON)."""
        key = self._preset_key(presets.kind)
        encoded = json.dumps(presets.items)
        row = await session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=encoded))
        else:
            row.value = encoded
        await session.commit()
        return presets
