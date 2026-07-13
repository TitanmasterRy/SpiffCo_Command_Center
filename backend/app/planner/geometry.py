"""Pure grid geometry for the planner (footprints, bounds, overlap).

Kept free of I/O and ORM so it is trivially unit-testable and shared by both
validation and summary code. Building footprints in ``buildings.json`` are in
meters; a grid cell spans ``cell_cm`` centimeters, so a footprint occupies
``ceil(meters * 100 / cell_cm)`` cells per axis. A rotation of 90°/270° swaps
the footprint's width and length.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.planner import Footprint, GridSpec, Placement


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle in cell coordinates (``x``/``y`` top-left)."""

    x: int
    y: int
    width: int
    length: int

    def overlaps(self, other: Rect) -> bool:
        """True if the two rectangles share any cell."""
        return (
            self.x < other.x + other.width
            and other.x < self.x + self.width
            and self.y < other.y + other.length
            and other.y < self.y + self.length
        )

    def within(self, grid: GridSpec) -> bool:
        """True if the rectangle lies fully inside the grid bounds."""
        return (
            self.x >= 0
            and self.y >= 0
            and self.x + self.width <= grid.width
            and self.y + self.length <= grid.length
        )


def footprint_cells(footprint: Footprint, cell_cm: int) -> tuple[int, int]:
    """Convert a meter footprint to (width_cells, length_cells) for ``cell_cm``."""
    width = max(1, math.ceil(footprint.width * 100 / cell_cm))
    length = max(1, math.ceil(footprint.length * 100 / cell_cm))
    return width, length


def placement_rect(placement: Placement, footprint: Footprint, cell_cm: int) -> Rect:
    """Occupied rectangle for a placement, accounting for rotation."""
    width, length = footprint_cells(footprint, cell_cm)
    if placement.rotation in (90, 270):
        width, length = length, width
    return Rect(x=placement.x, y=placement.y, width=width, length=length)
