"""Public schemas for the admin panel (auth, cheat catalog, execution)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ParamType = Literal["number", "slider", "text", "select", "item", "coords"]
ControlType = Literal["button", "toggle"]


class LoginRequest(BaseModel):
    """Credentials submitted to the admin login endpoint."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class SessionInfo(BaseModel):
    """An authenticated admin session."""

    token: str
    username: str
    expires_at: datetime


class CheatParam(BaseModel):
    """One input a cheat action takes, rendered generically by the frontend."""

    name: str
    label: str
    type: ParamType
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    default: Any | None = None
    unit: str | None = None


class CheatAction(BaseModel):
    """A single admin action (button press or toggle)."""

    id: str
    label: str
    control: ControlType = "button"
    params: list[CheatParam] = Field(default_factory=list)
    danger: bool = False
    hint: str | None = None
    # "player": targets one player — the UI shows an online-player selector and
    # sends the choice as params["player"] (empty = first player).
    # "world": acts on shared world state; no player selector.
    scope: Literal["player", "world"] = "world"
    # True when the action alters state shared by every player on the server
    # (research, factories, storage, time, ...). The UI badges these.
    affects_all: bool = False


class CheatSection(BaseModel):
    """A titled group of actions inside a category."""

    id: str
    label: str
    actions: list[CheatAction]


class CheatCategory(BaseModel):
    """A top-level admin panel tab (e.g. Player, Building, Power)."""

    id: str
    label: str
    icon: str
    sections: list[CheatSection]


class CheatCatalog(BaseModel):
    """The full tree of admin actions plus dispatch capability info."""

    categories: list[CheatCategory]
    executor: Literal["command_endpoint", "simulated"]
    executor_hint: str


class BridgeActions(BaseModel):
    """Which catalog actions the connected game bridge can actually perform.

    ``supported=None`` means capability is unknown (simulated executor, or the
    bridge is unreachable) — the panel then disables nothing.
    """

    executor: Literal["command_endpoint", "simulated"]
    supported: list[str] | None = None


class SpawnItemInfo(BaseModel):
    """One entry in the full in-game item catalogue (the spawn picker's source).

    ``class_name`` is the game descriptor class (``Desc_IronPlate_C``) sent to the
    bridge to spawn the item; the rest is for display, search, and grouping.
    """

    class_name: str
    name: str
    category: str
    form: Literal["solid", "liquid", "gas"] = "solid"
    stack_size: int = 0
    sink_points: int = 0


class CheatExecuteRequest(BaseModel):
    """Request to run one cheat action."""

    action_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class CheatExecuteResult(BaseModel):
    """Outcome of a cheat execution."""

    action_id: str
    status: Literal["executed", "simulated"]
    detail: str
    toggles: dict[str, bool]
    response: dict[str, Any] = Field(default_factory=dict)


class CheatLogEntry(BaseModel):
    """One entry in the admin command audit log."""

    timestamp: datetime
    username: str
    action_id: str
    params: dict[str, Any]
    status: str


class AdminState(BaseModel):
    """Current server-tracked toggle states."""

    toggles: dict[str, bool]


class PresetList(BaseModel):
    """A named collection of saved presets (teleports, inventories, ...)."""

    kind: str
    items: list[dict[str, Any]] = Field(default_factory=list)
