"""Pure analytics math: series statistics, uptime, and window comparison.

No I/O — operates on plain float sequences so it is trivially unit-testable and
reused by the service, which supplies values pulled from the history tables.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.schemas.analytics import Comparison, SeriesStats


def series_stats(values: Sequence[float]) -> SeriesStats:
    """Min/max/avg/latest for a series (zeros for an empty series)."""
    if not values:
        return SeriesStats(count=0)
    return SeriesStats(
        count=len(values),
        min=round(min(values), 4),
        max=round(max(values), 4),
        avg=round(sum(values) / len(values), 4),
        latest=round(values[-1], 4),
    )


def uptime_fraction(pairs: Sequence[tuple[float, float]]) -> float:
    """Fraction of (produced, consumed) samples where produced >= consumed."""
    if not pairs:
        return 0.0
    healthy = sum(1 for produced, consumed in pairs if produced >= consumed)
    return round(healthy / len(pairs), 4)


def compare(values: Sequence[float]) -> Comparison:
    """Compare the recent half of a series against the older half.

    With fewer than two samples there is nothing to compare, so both halves equal
    the single value (zero delta).
    """
    if len(values) < 2:
        only = values[-1] if values else 0.0
        return Comparison(current_avg=only, previous_avg=only, delta=0.0, delta_percent=0.0)
    mid = len(values) // 2
    previous = values[:mid]
    current = values[mid:]
    prev_avg = sum(previous) / len(previous)
    cur_avg = sum(current) / len(current)
    delta = cur_avg - prev_avg
    pct = round(delta / prev_avg, 4) if abs(prev_avg) > 1e-9 else None
    return Comparison(
        current_avg=round(cur_avg, 4),
        previous_avg=round(prev_avg, 4),
        delta=round(delta, 4),
        delta_percent=pct,
    )
