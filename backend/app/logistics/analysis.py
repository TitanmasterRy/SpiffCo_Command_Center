"""Pure logistics network analysis (throughput / utilization rollups).

No I/O or ORM — trivially unit-testable and shared by the provider and service.
"""

from __future__ import annotations

from app.schemas.logistics import LogisticsNode, LogisticsRoute, LogisticsSummary


def summarize(nodes: list[LogisticsNode], routes: list[LogisticsRoute]) -> LogisticsSummary:
    """Roll up node/route counts, per-mode throughput, and over-capacity routes."""
    throughput_by_mode: dict[str, float] = {}
    over_capacity: list[str] = []
    max_util = 0.0
    for route in routes:
        throughput_by_mode[route.mode] = (
            throughput_by_mode.get(route.mode, 0.0) + route.throughput_per_min
        )
        if route.over_capacity:
            over_capacity.append(route.id)
        max_util = max(max_util, route.utilization)
    return LogisticsSummary(
        route_count=len(routes),
        node_count=len(nodes),
        over_capacity_routes=over_capacity,
        throughput_by_mode={k: round(v, 3) for k, v in throughput_by_mode.items()},
        max_utilization=round(max_util, 4),
    )
