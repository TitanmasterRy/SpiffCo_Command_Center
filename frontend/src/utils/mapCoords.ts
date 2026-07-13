import type { Position } from '../types/world';

/**
 * Game-world → Leaflet coordinate conversion.
 *
 * The game uses centimeters with +y pointing south. We render on `CRS.Simple`
 * in kilometer units with north up, so: lat = -y/1000, lng = x/1000.
 */
export const CM_PER_UNIT = 1000; // 1 map unit = 1 km

export function toLatLng(position: Position): [number, number] {
  return [-position.y / CM_PER_UNIT, position.x / CM_PER_UNIT];
}

/** Inverse of {@link toLatLng} (z is unknowable from the map; defaults 0). */
export function fromLatLng(lat: number, lng: number): Position {
  return { x: lng * CM_PER_UNIT, y: -lat * CM_PER_UNIT, z: 0 };
}

/**
 * Game-coordinate extent (cm) of the in-game map image, taken verbatim from the
 * Ficsit Remote Monitoring web UI: `bounds:[-324698.168,-375000,425301.832,375000]`
 * as `[minX, minY, maxX, maxY]`. Converting both corners through {@link toLatLng}
 * puts the image in the exact same space as every plotted feature, so they align.
 */
const MAP_GAME_BOUNDS = { minX: -324698.16796875, minY: -375000, maxX: 425301.83203125, maxY: 375000 };

/** Leaflet `[[lat,lng],[lat,lng]]` bounds for the map background ImageOverlay. */
export const MAP_IMAGE_BOUNDS: [[number, number], [number, number]] = [
  toLatLng({ x: MAP_GAME_BOUNDS.minX, y: MAP_GAME_BOUNDS.minY, z: 0 }),
  toLatLng({ x: MAP_GAME_BOUNDS.maxX, y: MAP_GAME_BOUNDS.maxY, z: 0 }),
];

/** Public path to the bundled in-game map render (see `public/assets/`). */
export const MAP_IMAGE_URL = '/assets/satisfactory-map.avif';
