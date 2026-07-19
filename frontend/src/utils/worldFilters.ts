import type { FeatureType, MapFeature } from '../types/world';
import { featureLayerId } from './scimLayers';

export interface WorldFilters {
  /**
   * Per-layer visibility keyed by SCIM layer id (`ironPure`, `somersloops`, …)
   * or the `live:<type>` fallback for features without a SCIM layer
   * (`live:factory`, …). Missing keys mean hidden.
   */
  activeLayers: Record<string, boolean>;
  /** Case-insensitive name substring; '' disables. */
  search: string;
  /** Drop pickups whose collected === true. */
  hideCollected: boolean;
  /** Node-like features: 'all' | 'free' | 'occupied'. */
  nodeStatus: 'all' | 'free' | 'occupied';
  /** Factories: keep only those whose meta.produces includes this item ('all' disables). */
  produces: string;
  /**
   * Keep only features whose meta.region matches ('all' disables).
   * Features without a region (built infrastructure) are hidden while a
   * specific region is selected — the view answers "what does this region offer".
   */
  region: string;
}

/** Feature types treated as collectible "pickups". */
export const PICKUP_TYPES: ReadonlySet<FeatureType> = new Set(['artifact', 'collectible', 'wreck']);

/** Node-like feature types that share the miner-status filter. */
export const NODE_LIKE_TYPES: ReadonlySet<FeatureType> = new Set([
  'resource_node',
  'geyser',
  'resource_well',
]);

/** The pickup kind of a feature ('' if none). */
export function pickupKind(feature: MapFeature): string {
  return String(feature.meta.kind ?? '');
}

/** Split a factory's ``meta.produces`` comma list into individual item names. */
function producesList(feature: MapFeature): string[] {
  return String(feature.meta.produces ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Apply all map filters; single source of truth for the WorldMap view. */
export function applyWorldFilters(features: MapFeature[], filters: WorldFilters): MapFeature[] {
  const query = filters.search.trim().toLowerCase();
  return features.filter((f) => {
    if (!filters.activeLayers[featureLayerId(f)]) return false;
    if (filters.hideCollected && f.collected === true) return false;
    if (query && !f.name.toLowerCase().includes(query)) return false;
    if (filters.region !== 'all' && String(f.meta.region ?? '') !== filters.region) return false;
    return passesNodeStatus(f, filters) && passesProduces(f, filters);
  });
}

/** Node-like miner-status filter. */
function passesNodeStatus(f: MapFeature, filters: WorldFilters): boolean {
  if (!NODE_LIKE_TYPES.has(f.type)) return true;
  if (filters.nodeStatus === 'free' && f.occupied === true) return false;
  if (filters.nodeStatus === 'occupied' && f.occupied !== true) return false;
  return true;
}

/** Factory-only produced-item filter. */
function passesProduces(f: MapFeature, filters: WorldFilters): boolean {
  if (filters.produces === 'all' || f.type !== 'factory') return true;
  return producesList(f).includes(filters.produces);
}

/** Distinct, sorted values of a meta key across features (for filter options). */
export function metaOptions(features: MapFeature[], key: string): string[] {
  return [...new Set(features.map((f) => String(f.meta[key] ?? '')).filter(Boolean))].sort();
}

/** Distinct, sorted output items across all factory features (for the produces filter). */
export function producesOptions(features: MapFeature[]): string[] {
  const items = new Set<string>();
  for (const f of features) {
    if (f.type === 'factory') for (const item of producesList(f)) items.add(item);
  }
  return [...items].sort();
}
