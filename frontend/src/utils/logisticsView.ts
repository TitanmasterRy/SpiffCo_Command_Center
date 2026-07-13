import type { LogisticsNode } from '../types/logistics';

/**
 * Pure helpers for the logistics schematic: a green→amber→red utilization scale
 * and a world-position→viewport projection. Kept side-effect free for testing.
 */

// Validated dark categorical anchors: green (ok) → yellow (busy) → red (over).
const UTIL_OK = '#199e70';
const UTIL_BUSY = '#c98500';
const UTIL_HOT = '#d95926';
const UTIL_OVER = '#e66767';

/** Color a route by utilization (0..1+); >1 means over capacity. */
export function utilizationColor(utilization: number): string {
  if (utilization > 1) return UTIL_OVER;
  if (utilization >= 0.85) return UTIL_HOT;
  if (utilization >= 0.6) return UTIL_BUSY;
  return UTIL_OK;
}

export interface Viewport {
  width: number;
  height: number;
  padding: number;
}

export type Projector = (position: { x: number; y: number }) => { x: number; y: number };

/**
 * Build a projector mapping world coordinates into a padded viewport, preserving
 * aspect ratio and flipping Y so +y (south) renders downward. Degenerate spreads
 * collapse to the viewport center.
 */
export function makeProjector(nodes: LogisticsNode[], view: Viewport): Projector {
  const xs = nodes.map((n) => n.position.x);
  const ys = nodes.map((n) => n.position.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const inner = { w: view.width - view.padding * 2, h: view.height - view.padding * 2 };
  const scale = Math.min(inner.w / spanX, inner.h / spanY);
  // Center the scaled content within the viewport.
  const offsetX = (inner.w - spanX * scale) / 2;
  const offsetY = (inner.h - spanY * scale) / 2;
  return (position) => ({
    x: view.padding + offsetX + (position.x - minX) * scale,
    y: view.padding + offsetY + (position.y - minY) * scale,
  });
}

/** Stroke width scaled by throughput (min 1.5, capped for very large flows). */
export function routeWidth(throughputPerMin: number): number {
  return Math.max(1.5, Math.min(8, throughputPerMin / 120));
}
