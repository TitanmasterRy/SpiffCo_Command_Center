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
