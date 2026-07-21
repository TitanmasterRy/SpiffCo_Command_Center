"""Permission catalog and role presets for user authorization.

A *permission* is a stable string key. ``view:*`` keys gate which pages a user
sees in the UI (enforced in the frontend nav/routing); action keys such as
``use:admin-cheats`` and ``manage:users`` gate privileged operations and are
enforced on the backend. Effective permissions are stored per user as an
explicit list, so an admin can start from a role preset and then customize.
"""

from __future__ import annotations

from typing import Final

# --- Page-view permissions (one per navigable area) ------------------------

VIEW_PERMISSIONS: Final[dict[str, str]] = {
    "view:dashboard": "Dashboard",
    "view:map": "World Map",
    "view:factories": "Factories",
    "view:factory-planner": "Factory Planner",
    "view:planner": "Production Planner",
    "view:power": "Power",
    "view:resources": "Resources",
    "view:logistics": "Logistics",
    "view:blueprints": "Blueprints",
    "view:analytics": "Analytics",
    "view:advisor": "Advisor",
    "view:offline": "Offline Mode",
    "view:settings": "Settings",
}

# --- Action permissions (privileged; enforced on the backend) --------------

ACTION_PERMISSIONS: Final[dict[str, str]] = {
    "use:admin-cheats": "Use the admin cheat panel",
    "manage:users": "Approve accounts and manage permissions",
}

#: Every permission key the system understands, mapped to a human label.
ALL_PERMISSIONS: Final[dict[str, str]] = {**VIEW_PERMISSIONS, **ACTION_PERMISSIONS}

#: Ordered list of every permission key (stable for UI rendering).
PERMISSION_KEYS: Final[list[str]] = list(ALL_PERMISSIONS)

# --- Role presets ----------------------------------------------------------

#: A viewer can read every page except Settings; no privileged actions.
_VIEWER: Final[list[str]] = [k for k in VIEW_PERMISSIONS if k != "view:settings"]

#: An operator can read everything (incl. Settings) and run cheat actions.
_OPERATOR: Final[list[str]] = [*VIEW_PERMISSIONS, "use:admin-cheats"]

#: An admin has every permission.
_ADMIN: Final[list[str]] = PERMISSION_KEYS

ROLE_PRESETS: Final[dict[str, list[str]]] = {
    "viewer": _VIEWER,
    "operator": _OPERATOR,
    "admin": _ADMIN,
}

ROLES: Final[list[str]] = list(ROLE_PRESETS)


def preset_permissions(role: str) -> list[str]:
    """Return the default permission list for *role* (empty if unknown)."""
    return list(ROLE_PRESETS.get(role, []))


def sanitize_permissions(permissions: list[str]) -> list[str]:
    """Drop unknown keys and de-duplicate, preserving catalog order."""
    granted = set(permissions)
    return [key for key in PERMISSION_KEYS if key in granted]
