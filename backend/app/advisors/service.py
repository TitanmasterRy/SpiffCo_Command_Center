"""Advisor service: assemble a ranked report from live snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from app.advisors.engine import build_findings
from app.schemas.advisor import AdvisorReport
from app.schemas.dashboard import DashboardSnapshot
from app.schemas.logistics import LogisticsSnapshot


def build_report(
    dashboard: DashboardSnapshot, logistics: LogisticsSnapshot
) -> AdvisorReport:
    """Run the advisor rules and count findings by severity."""
    findings = build_findings(dashboard, logistics)
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return AdvisorReport(
        generated_at=datetime.now(UTC),
        source=dashboard.source,
        findings=findings,
        counts=counts,
    )
