import { describe, expect, it } from 'vitest';
import { fromLatLng, MAP_BOUNDS, toLatLng, ZOOM_RATIO } from '../utils/mapCoords';

describe('map coordinate conversion (SCIM projection)', () => {
  it('maps the extended map corners onto the tile pyramid extent', () => {
    // Extended west/north corner → CRS origin; east/south → pyramid far corner.
    const [north, west] = toLatLng({ x: -324698.832031 - 93750.083, y: -375000 - 93750, z: 0 });
    expect(north).toBeCloseTo(0, 3);
    expect(west).toBeCloseTo(0, 3);
    const [south, east] = toLatLng({ x: 425301.832031 + 93750.083, y: 375000 + 93750, z: 0 });
    expect(south).toBeCloseTo(MAP_BOUNDS[0][0], 3);
    expect(east).toBeCloseTo(MAP_BOUNDS[1][1], 3);
  });

  it('keeps north up (smaller y → greater lat)', () => {
    const [latNorth] = toLatLng({ x: 0, y: -100_000, z: 0 });
    const [latSouth] = toLatLng({ x: 0, y: 100_000, z: 0 });
    expect(latNorth).toBeGreaterThan(latSouth);
  });

  it('round-trips through fromLatLng', () => {
    const position = { x: -72_000, y: 148_000, z: 0 };
    const [lat, lng] = toLatLng(position);
    const back = fromLatLng(lat, lng);
    expect(back.x).toBeCloseTo(position.x, 5);
    expect(back.y).toBeCloseTo(position.y, 5);
  });

  it('uses SCIM zoom addressing (zoomRatio 8)', () => {
    expect(ZOOM_RATIO).toBe(8);
  });
});
