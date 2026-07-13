"""FRM-backed providers implementing the sync ``snapshot()`` protocols.

Each provider returns the connector's latest cached, normalized snapshot, so the
existing services (`GameStateService`, `WorldService`, `LogisticsService`) work
unchanged whether backed by simulation or FRM.
"""

from __future__ import annotations

from app.connectors.frm.connector import FrmConnector
from app.schemas.dashboard import DashboardSnapshot
from app.schemas.logistics import LogisticsSnapshot
from app.schemas.world import WorldSnapshot


class FrmGameProvider:
    """Game-state provider backed by the FRM connector."""

    def __init__(self, connector: FrmConnector) -> None:
        self._connector = connector

    def snapshot(self) -> DashboardSnapshot:
        return self._connector.dashboard_snapshot()


class FrmWorldProvider:
    """World provider backed by the FRM connector."""

    def __init__(self, connector: FrmConnector) -> None:
        self._connector = connector

    def snapshot(self) -> WorldSnapshot:
        return self._connector.world_snapshot()


class FrmLogisticsProvider:
    """Logistics provider backed by the FRM connector."""

    def __init__(self, connector: FrmConnector) -> None:
        self._connector = connector

    def snapshot(self) -> LogisticsSnapshot:
        return self._connector.logistics_snapshot()
