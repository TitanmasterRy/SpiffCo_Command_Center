import { describe, expect, it } from 'vitest';
import type { BuildingInfo, Layout, Placement } from '../types/planner';
import {
  footprintCells,
  invalidPlacementIds,
  nextRotation,
  pixelToCell,
  placementPower,
  placementRect,
  rectsOverlap,
  rectWithin,
} from '../utils/plannerGrid';

const SMELTER: BuildingInfo = {
  id: 'smelter',
  name: 'Smelter',
  category: 'production',
  power_mw: 4,
  inputs: 1,
  outputs: 1,
  footprint: { width: 6, length: 9 },
  build_cost: { 'iron-rod': 5, wire: 8 },
};

const BUILDINGS = { smelter: SMELTER };

const placement = (partial: Partial<Placement>): Placement => ({
  id: 'p',
  building: 'smelter',
  x: 0,
  y: 0,
  rotation: 0,
  clock: 1,
  ...partial,
});

const layout = (placements: Placement[], width = 40, length = 40): Layout => ({
  grid: { width, length, cell_cm: 100 },
  placements,
});

describe('footprint + rect geometry', () => {
  it('converts meters to cells by cell size', () => {
    expect(footprintCells(SMELTER.footprint, 100)).toEqual({ width: 6, length: 9 });
    expect(footprintCells(SMELTER.footprint, 50)).toEqual({ width: 12, length: 18 });
  });

  it('swaps width/length on 90/270 rotation', () => {
    expect(placementRect(placement({ rotation: 90 }), SMELTER.footprint, 100)).toMatchObject({
      width: 9,
      length: 6,
    });
    expect(placementRect(placement({ rotation: 0 }), SMELTER.footprint, 100)).toMatchObject({
      width: 6,
      length: 9,
    });
  });

  it('detects overlap and edge-touching', () => {
    expect(rectsOverlap({ x: 0, y: 0, width: 5, length: 5 }, { x: 4, y: 4, width: 3, length: 3 })).toBe(true);
    expect(rectsOverlap({ x: 0, y: 0, width: 4, length: 4 }, { x: 4, y: 0, width: 4, length: 4 })).toBe(false);
  });

  it('checks grid bounds', () => {
    const grid = { width: 10, length: 10, cell_cm: 100 };
    expect(rectWithin({ x: 0, y: 0, width: 10, length: 10 }, grid)).toBe(true);
    expect(rectWithin({ x: 6, y: 6, width: 6, length: 6 }, grid)).toBe(false);
  });
});

describe('invalidPlacementIds', () => {
  it('flags overlapping placements', () => {
    const ids = invalidPlacementIds(
      layout([placement({ id: 'a', x: 0, y: 0 }), placement({ id: 'b', x: 2, y: 2 })]),
      BUILDINGS,
    );
    expect(ids).toEqual(new Set(['a', 'b']));
  });

  it('passes non-overlapping placements', () => {
    const ids = invalidPlacementIds(
      layout([placement({ id: 'a', x: 0, y: 0 }), placement({ id: 'b', x: 10, y: 0 })]),
      BUILDINGS,
    );
    expect(ids.size).toBe(0);
  });

  it('flags out-of-bounds and unknown buildings', () => {
    const ids = invalidPlacementIds(
      layout(
        [placement({ id: 'a', x: 38, y: 38 }), placement({ id: 'b', building: 'nope', x: 0, y: 0 })],
        40,
        40,
      ),
      BUILDINGS,
    );
    expect(ids).toEqual(new Set(['a', 'b']));
  });
});

describe('helpers', () => {
  it('cycles rotations clockwise', () => {
    expect(nextRotation(0)).toBe(90);
    expect(nextRotation(270)).toBe(0);
  });

  it('computes super-linear clock power', () => {
    expect(placementPower(SMELTER, 1)).toBeCloseTo(4, 5);
    expect(placementPower(SMELTER, 2)).toBeCloseTo(4 * 2 ** 1.321928, 4);
  });

  it('maps pixels to clamped cells', () => {
    expect(pixelToCell(0, 16, 40)).toBe(0);
    expect(pixelToCell(35, 16, 40)).toBe(2);
    expect(pixelToCell(9999, 16, 40)).toBe(39);
  });
});
