"""Schemas for the AI advisor: explained findings and a ranked report.

The advisor consolidates rule-based detection (power shortfall, starving/idle
machines, production shortages, storage backing up, logistics bottlenecks, low
uptime) into one ranked list, each finding carrying a plain-language explanation
and a suggested fix.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dashboard import Severity

FindingCategory = Literal[
    "power",
    "machines",
    "production",
    "storage",
    "logistics",
    "uptime",
    "general",
]


class AdvisorFinding(BaseModel):
    """One explained recommendation from the advisor."""

    id: str = Field(description="Stable id, e.g. 'production:iron-plate'")
    severity: Severity
    category: FindingCategory
    title: str
    explanation: str = Field(description="Why this was flagged")
    suggestion: str = Field(description="What to do about it")


class AdvisorReport(BaseModel):
    """Ranked advisor findings plus per-severity counts."""

    generated_at: datetime
    source: Literal["simulation", "frm", "save"]
    findings: list[AdvisorFinding]
    counts: dict[str, int] = Field(description="severity -> count")
