"""Ficsit Remote Monitoring connector (Phase 11).

Polls the FRM mod, normalizes raw payloads into internal schemas, and exposes
FRM-backed providers that satisfy the same ``snapshot()`` protocols as the
simulated providers. Raw FRM shapes never leave this package.
"""

from app.connectors.frm.client import FrmClient
from app.connectors.frm.connector import ConnectionState, FrmConnector
from app.connectors.frm.providers import (
    FrmGameProvider,
    FrmLogisticsProvider,
    FrmWorldProvider,
)

__all__ = [
    "FrmConnector",
    "ConnectionState",
    "FrmClient",
    "FrmGameProvider",
    "FrmWorldProvider",
    "FrmLogisticsProvider",
]
