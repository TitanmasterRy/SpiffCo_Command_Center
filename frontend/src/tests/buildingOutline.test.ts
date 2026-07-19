import { describe, expect, it } from 'vitest';
import { buildingOutline, type BuildingModel } from '../utils/buildingOutline';
import { fromLatLng } from '../utils/mapCoords';

const center = { x: 10_000, y: -5_000, z: 0 };

/** Convert an outline ring back to game cm relative to the center. */
function relative(ringLatLng: [number, number][]): [number, number][] {
  return ringLatLng.map(([lat, lng]) => {
    const p = fromLatLng(lat, lng);
    return [p.x - center.x, p.y - center.y];
  });
}

describe('buildingOutline', () => {
  it('returns null without a model or footprint', () => {
    expect(buildingOutline(undefined, center, 0)).toBeNull();
    expect(buildingOutline({ name: 'x' }, center, 0)).toBeNull();
  });

  it('scales and translates detailed forms', () => {
    const model: BuildingModel = { scale: 2, forms: [{ points: [[100, 0], [0, 50]] }] };
    const rings = buildingOutline(model, center, 0)!;
    const rel = relative(rings[0][0]);
    expect(rel[0][0]).toBeCloseTo(200, 3);
    expect(rel[0][1]).toBeCloseTo(0, 3);
    expect(rel[1][1]).toBeCloseTo(100, 3);
  });

  it('rotates points by the building yaw', () => {
    const model: BuildingModel = { forms: [{ points: [[100, 0]] }] };
    const rel = relative(buildingOutline(model, center, 90)![0][0]);
    // 90° yaw turns +x into +y.
    expect(rel[0][0]).toBeCloseTo(0, 3);
    expect(rel[0][1]).toBeCloseTo(100, 3);
  });

  it('falls back to a width × length rectangle (meters → cm)', () => {
    const model: BuildingModel = { width: 6, length: 9 };
    const rings = buildingOutline(model, center, 0)!;
    const rel = relative(rings[0][0]);
    expect(rel).toHaveLength(4);
    expect(rel[0][0]).toBeCloseTo(-300, 2);
    expect(rel[0][1]).toBeCloseTo(-450, 2);
    expect(rel[2][0]).toBeCloseTo(300, 2);
    expect(rel[2][1]).toBeCloseTo(450, 2);
  });
});
