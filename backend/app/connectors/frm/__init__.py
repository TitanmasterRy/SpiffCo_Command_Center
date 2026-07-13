"""Ficsit Remote Monitoring connector (full implementation in Phase 11).

Phase 1 defines only the public interface so other layers can code against it:
:class:`FrmConnector` in :mod:`app.connectors.frm.connector`.
"""

from app.connectors.frm.connector import ConnectionState, FrmConnector

__all__ = ["FrmConnector", "ConnectionState"]
