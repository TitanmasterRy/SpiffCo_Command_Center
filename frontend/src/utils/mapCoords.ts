import type { Position } from '../types/world';

/**
 * Game-world → Leaflet coordinate conversion, using SCIM's projection.
 *
 * SCIM (satisfactory-calculator.com's Interactive Map) renders the world on
 * `CRS.Simple` against a square raster of `BACKGROUND_SIZE` pixels covering the
 * game-map extent plus an extra border, addressed at `ZOOM_RATIO` (the zoom at
 * which one raster pixel equals one CRS unit / 2^ZOOM_RATIO). Adopting the same
 * projection makes their public map tile pyramid line up exactly, so the map
 * gets SCIM's game/realistic tile renders while all live features keep working.
 *
 * Constants mirror `GameMap.js` in the SCIM source (after its `start()` border
 * extension): base bounds from the in-game map actor, extended by
 * `EXTRA_BACKGROUND` raster pixels on every side.
 */

// Base game-map extent in cm (Unreal units); +x east, +y south.
const BASE_WEST = -324698.832031;
const BASE_EAST = 425301.832031;
const BASE_NORTH = -375000;
const BASE_SOUTH = 375000;

const BASE_BACKGROUND = 32768; // raster px of the unextended map
const EXTRA_BACKGROUND = 4096; // extra border px on each side
const TILE_SIZE = 256;

/** Total raster size (px) including the extra border. */
const BACKGROUND_SIZE = BASE_BACKGROUND + EXTRA_BACKGROUND * 2;

// cm added per side by the border extension (cm-per-px × border px).
const WEST_OFFSET = ((Math.abs(BASE_WEST) + Math.abs(BASE_EAST)) / BASE_BACKGROUND) * EXTRA_BACKGROUND;
const NORTH_OFFSET = ((Math.abs(BASE_NORTH) + Math.abs(BASE_SOUTH)) / BASE_BACKGROUND) * EXTRA_BACKGROUND;

const WEST = BASE_WEST - WEST_OFFSET;
const EAST = BASE_EAST + WEST_OFFSET;
const NORTH = BASE_NORTH - NORTH_OFFSET;
const SOUTH = BASE_SOUTH + NORTH_OFFSET;

const X_MAX = Math.abs(WEST) + Math.abs(EAST);
const Y_MAX = Math.abs(NORTH) + Math.abs(SOUTH);
const X_RATIO = BACKGROUND_SIZE / X_MAX; // raster px per cm
const Y_RATIO = BACKGROUND_SIZE / Y_MAX;

/** Zoom level at which raster pixels map 1:1 to CRS points (SCIM's zoomRatio). */
export const ZOOM_RATIO = Math.ceil(Math.log(BACKGROUND_SIZE / TILE_SIZE) / Math.LN2);
const SCALE = 2 ** ZOOM_RATIO; // CRS.Simple scale factor at ZOOM_RATIO

/** Tile zoom range of the SCIM pyramid; the map can overzoom past native. */
export const MIN_TILE_ZOOM = 3;
export const MAX_NATIVE_ZOOM = 8;
export const MAX_ZOOM = MAX_NATIVE_ZOOM + 4;

export function toLatLng(position: Position): [number, number] {
  const rasterX = (X_MAX - EAST + position.x) * X_RATIO;
  const rasterY = (Y_MAX - NORTH + position.y) * Y_RATIO - BACKGROUND_SIZE;
  return [-rasterY / SCALE, rasterX / SCALE];
}

/** Inverse of {@link toLatLng} (z is unknowable from the map; defaults 0). */
export function fromLatLng(lat: number, lng: number): Position {
  const rasterX = lng * SCALE;
  const rasterY = -lat * SCALE;
  return {
    x: rasterX / X_RATIO - (X_MAX - EAST),
    y: (rasterY + BACKGROUND_SIZE) / Y_RATIO - (Y_MAX - NORTH),
    z: 0,
  };
}

/** Full tile-pyramid extent (game map + border) as Leaflet bounds. */
export const MAP_BOUNDS: [[number, number], [number, number]] = [
  [-BACKGROUND_SIZE / SCALE, 0],
  [0, BACKGROUND_SIZE / SCALE],
];

/** Center of the map, for the default view. */
export const MAP_CENTER: [number, number] = [
  -BACKGROUND_SIZE / SCALE / 2,
  BACKGROUND_SIZE / SCALE / 2,
];

/**
 * SCIM's public tile pyramids (game render and realistic satellite-style
 * render). Used as the primary base layers; requires internet access.
 */
export function scimTileUrl(layer: 'gameLayer' | 'realisticLayer'): string {
  return `https://static.satisfactory-calculator.com/imgMap/${layer}/Stable/{z}/{x}/{y}.png`;
}

/**
 * Game-coordinate extent (cm) of the bundled offline map render — the
 * unextended in-game map bounds. Converting both corners through
 * {@link toLatLng} keeps the image aligned with plotted features.
 */
export const MAP_IMAGE_BOUNDS: [[number, number], [number, number]] = [
  toLatLng({ x: BASE_WEST, y: BASE_NORTH, z: 0 }),
  toLatLng({ x: BASE_EAST, y: BASE_SOUTH, z: 0 }),
];

/** Public path to the bundled in-game map render (offline fallback). */
export const MAP_IMAGE_URL = '/assets/satisfactory-map.avif';
