import { describe, expect, it } from 'vitest';
import { fromLatLng, toLatLng } from '../utils/mapCoords';

describe('map coordinate conversion', () => {
  it('converts game cm to leaflet km with north up', () => {
    expect(toLatLng({ x: 100_000, y: -50_000, z: 0 })).toEqual([50, 100]);
  });

  it('round-trips through fromLatLng', () => {
    const position = { x: -72_000, y: 148_000, z: 0 };
    const [lat, lng] = toLatLng(position);
    expect(fromLatLng(lat, lng)).toEqual(position);
  });
});
