import type { BuildingInfo, Footprint, GridSpec, Layout, Placement, Rotation } from '../types/planner';

/**
 * Pure grid math for the factory planner, mirroring the backend geometry so the
 * editor can highlight collisions/out-of-bounds live before a save is attempted.
 * A grid cell spans `cell_cm` centimeters; footprints (in meters) occupy
 * `ceil(m * 100 / cell_cm)` cells per axis. Rotation 90/270 swaps width/length.
 */

export interface Rect {
  x: number;
  y: number;
  width: number;
  length: number;
}

export const ROTATIONS: Rotation[] = [0, 90, 180, 270];

/** Next 90° rotation clockwise. */
export function nextRotation(rotation: Rotation): Rotation {
  return ROTATIONS[(ROTATIONS.indexOf(rotation) + 1) % ROTATIONS.length];
}

/** Footprint in cells for a given cell size (before rotation). */
export function footprintCells(footprint: Footprint, cellCm: number): { width: number; length: number } {
  return {
    width: Math.max(1, Math.ceil((footprint.width * 100) / cellCm)),
    length: Math.max(1, Math.ceil((footprint.length * 100) / cellCm)),
  };
}

/** Occupied rectangle for a placement, accounting for rotation. */
export function placementRect(placement: Placement, footprint: Footprint, cellCm: number): Rect {
  const { width, length } = footprintCells(footprint, cellCm);
  const swapped = placement.rotation === 90 || placement.rotation === 270;
  return {
    x: placement.x,
    y: placement.y,
    width: swapped ? length : width,
    length: swapped ? width : length,
  };
}

/** True if two rectangles share any cell (touching edges do not count). */
export function rectsOverlap(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.width &&
    b.x < a.x + a.width &&
    a.y < b.y + b.length &&
    b.y < a.y + a.length
  );
}

/** True if a rectangle lies fully inside the grid bounds. */
export function rectWithin(rect: Rect, grid: GridSpec): boolean {
  return (
    rect.x >= 0 &&
    rect.y >= 0 &&
    rect.x + rect.width <= grid.width &&
    rect.y + rect.length <= grid.length
  );
}

/**
 * Ids of placements that overlap another placement or fall outside the grid.
 * Unknown buildings (not in `buildings`) are flagged too. Drives red highlights.
 */
export function invalidPlacementIds(
  layout: Layout,
  buildings: Record<string, BuildingInfo>,
): Set<string> {
  const invalid = new Set<string>();
  const rects: Array<{ placement: Placement; rect: Rect }> = [];
  for (const placement of layout.placements) {
    const building = buildings[placement.building];
    if (!building) {
      invalid.add(placement.id);
      continue;
    }
    const rect = placementRect(placement, building.footprint, layout.grid.cell_cm);
    if (!rectWithin(rect, layout.grid)) invalid.add(placement.id);
    rects.push({ placement, rect });
  }
  for (let i = 0; i < rects.length; i += 1) {
    for (let j = i + 1; j < rects.length; j += 1) {
      if (rectsOverlap(rects[i].rect, rects[j].rect)) {
        invalid.add(rects[i].placement.id);
        invalid.add(rects[j].placement.id);
      }
    }
  }
  return invalid;
}

// Satisfactory power scales super-linearly with clock: draw = base * clock^1.321928.
export const POWER_EXPONENT = 1.321928;

/** Power draw (MW) of a single placement at its clock. */
export function placementPower(building: BuildingInfo, clock: number): number {
  return building.power_mw * clock ** POWER_EXPONENT;
}

/** Convert a pixel offset within the grid SVG to a cell coordinate (clamped). */
export function pixelToCell(px: number, cellPx: number, max: number): number {
  return Math.max(0, Math.min(max - 1, Math.floor(px / cellPx)));
}
