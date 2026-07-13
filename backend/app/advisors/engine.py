"""Pure advisor rules: derive explained findings from live snapshots.

No I/O — takes normalized snapshots and returns findings, so every rule is
unit-testable against crafted inputs. The service wires in the live snapshots.
"""

from __future__ import annotations

from app.power import analysis as power_analysis
from app.schemas.advisor import AdvisorFinding
from app.schemas.dashboard import DashboardSnapshot
from app.schemas.logistics import LogisticsSnapshot

_SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}

# A production line below this fraction of its target counts as a shortage.
_SHORTAGE_RATIO = 0.9
# Storage at or above this fill fraction is backing up.
_STORAGE_FULL = 0.95


def _power_findings(dashboard: DashboardSnapshot) -> list[AdvisorFinding]:
    power = dashboard.power
    _, fraction, status = power_analysis.headroom(power)
    battery = power_analysis.battery(power)
    findings: list[AdvisorFinding] = []
    if status == "critical":
        findings.append(
            AdvisorFinding(
                id="power:capacity",
                severity="critical",
                category="power",
                title="Power demand exceeds capacity",
                explanation=(
                    f"Consumption ({power.consumed_mw:.0f} MW) is at or above capacity "
                    f"({power.capacity_mw:.0f} MW); the grid is one machine from a blackout."
                ),
                suggestion="Bring more generators online or switch off non-critical load.",
            )
        )
    elif fraction < 0.1:
        findings.append(
            AdvisorFinding(
                id="power:headroom",
                severity="warning",
                category="power",
                title="Low power headroom",
                explanation=f"Only {fraction * 100:.0f}% spare capacity remains.",
                suggestion="Add generation before expanding production.",
            )
        )
    if battery.trend == "draining" and battery.minutes_remaining is not None:
        severe = battery.minutes_remaining < 5
        findings.append(
            AdvisorFinding(
                id="power:battery",
                severity="critical" if severe else "warning",
                category="power",
                title="Battery draining",
                explanation=(
                    f"Batteries are discharging (~{battery.minutes_remaining:.0f} min to empty); "
                    "generation is below consumption."
                ),
                suggestion="Increase generation to cover the deficit before the reserve is gone.",
            )
        )
    return findings


def _machine_findings(dashboard: DashboardSnapshot) -> list[AdvisorFinding]:
    findings: list[AdvisorFinding] = []
    unpowered = dashboard.machines.unpowered
    if unpowered > 0:
        findings.append(
            AdvisorFinding(
                id="machines:unpowered",
                severity="warning",
                category="machines",
                title=f"{unpowered} machine(s) unpowered",
                explanation="Unpowered machines produce nothing and can starve downstream lines.",
                suggestion="Check the grid/fuse and reconnect power to the affected buildings.",
            )
        )
    return findings


def _factory_findings(dashboard: DashboardSnapshot) -> list[AdvisorFinding]:
    findings: list[AdvisorFinding] = []
    for factory in dashboard.factories:
        if factory.status == "error":
            findings.append(
                AdvisorFinding(
                    id=f"factory:{factory.id}",
                    severity="critical",
                    category="machines",
                    title=f"{factory.name} is down",
                    explanation=f"{factory.name} reports an error state at "
                    f"{factory.efficiency * 100:.0f}% efficiency.",
                    suggestion="Inspect the factory for a power loss or a jammed/starved machine.",
                )
            )
        elif factory.status == "warn":
            findings.append(
                AdvisorFinding(
                    id=f"factory:{factory.id}",
                    severity="warning",
                    category="machines",
                    title=f"{factory.name} underperforming",
                    explanation=f"{factory.name} is running at "
                    f"{factory.efficiency * 100:.0f}% of target.",
                    suggestion="Trace the limiting input — a starved belt or missing recipe input.",
                )
            )
    return findings


def _production_findings(dashboard: DashboardSnapshot) -> list[AdvisorFinding]:
    findings: list[AdvisorFinding] = []
    for stat in dashboard.production:
        if stat.target_per_min > 0 and stat.current_per_min < _SHORTAGE_RATIO * stat.target_per_min:
            ratio = stat.current_per_min / stat.target_per_min
            findings.append(
                AdvisorFinding(
                    id=f"production:{stat.item}",
                    severity="warning",
                    category="production",
                    title=f"{stat.name} below target",
                    explanation=(
                        f"{stat.name} is at {stat.current_per_min:.0f}/min "
                        f"({ratio * 100:.0f}% of the {stat.target_per_min:.0f}/min target)."
                    ),
                    suggestion="Check upstream supply and machine clocks feeding this item.",
                )
            )
    return findings


def _storage_findings(dashboard: DashboardSnapshot) -> list[AdvisorFinding]:
    findings: list[AdvisorFinding] = []
    for level in dashboard.storage:
        if level.capacity > 0 and level.stored / level.capacity >= _STORAGE_FULL:
            findings.append(
                AdvisorFinding(
                    id=f"storage:{level.item}",
                    severity="warning",
                    category="storage",
                    title=f"{level.name} storage almost full",
                    explanation=(
                        f"{level.name} is at "
                        f"{level.stored / level.capacity * 100:.0f}% — production will back up and "
                        "stall the machines feeding it."
                    ),
                    suggestion="Add a consumer or a sink, or expand storage for this item.",
                )
            )
    return findings


def _logistics_findings(logistics: LogisticsSnapshot) -> list[AdvisorFinding]:
    findings: list[AdvisorFinding] = []
    for route in logistics.routes:
        if route.over_capacity:
            findings.append(
                AdvisorFinding(
                    id=f"logistics:{route.id}",
                    severity="warning",
                    category="logistics",
                    title=f"{route.name} over capacity",
                    explanation=(
                        f"{route.name} demands {route.throughput_per_min:.0f}/min but its "
                        f"{route.mode} caps at {route.capacity_per_min:.0f}/min "
                        f"({route.utilization * 100:.0f}%)."
                    ),
                    suggestion="Upgrade the belt/pipe tier or split the flow across a second line.",
                )
            )
    return findings


def build_findings(
    dashboard: DashboardSnapshot, logistics: LogisticsSnapshot
) -> list[AdvisorFinding]:
    """Run every rule and return findings ranked by severity (then category)."""
    findings = [
        *_power_findings(dashboard),
        *_machine_findings(dashboard),
        *_factory_findings(dashboard),
        *_production_findings(dashboard),
        *_storage_findings(dashboard),
        *_logistics_findings(logistics),
    ]
    if not findings:
        findings.append(
            AdvisorFinding(
                id="general:ok",
                severity="info",
                category="general",
                title="All systems nominal",
                explanation="No bottlenecks, shortages, or power issues detected.",
                suggestion="Keep expanding — the factory has headroom.",
            )
        )
    findings.sort(key=lambda f: (_SEVERITY_RANK[f.severity], f.category, f.id))
    return findings
