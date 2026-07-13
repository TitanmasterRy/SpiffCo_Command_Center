import type { FeatureType, MapFeature } from '../types/world';

export interface WorldFilters {
  /** Per-type layer visibility. */
  visible: Record<FeatureType, boolean>;
  /** Case-insensitive name substring; '' disables. */
  search: string;
  /** Drop pickups whose collected === true. */
  hideCollected: boolean;
  /** Resource nodes: keep only this resource id ('all' disables). */
  resource: string;
  /** Resource nodes: keep only this purity ('all' disables). */
  purity: string;
  /** Resource nodes: 'all' | 'free' | 'occupied'. */
  nodeStatus: 'all' | 'free' | 'occupied';
  /** Pickups (artifact/collectible/wreck): keep only this meta.kind ('all' disables). */
  kind: string;
  /** Factories: keep only those whose meta.produces includes this item ('all' disables). */
  produces: string;
  /**
   * Keep only features whose meta.region matches ('all' disables).
   * Features without a region (built infrastructure) are hidden while a
   * specific region is selected — the view answers "what does this region offer".
   */
  region: string;
}

/** Feature types treated as collectible "pickups" for the kind filter. */
const PICKUP_TYPES: ReadonlySet<FeatureType> = new Set(['artifact', 'collectible', 'wreck']);

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
    if (!filters.visible[f.type]) return false;
    if (filters.hideCollected && f.collected === true) return false;
    if (query && !f.name.toLowerCase().includes(query)) return false;
    if (filters.region !== 'all' && String(f.meta.region ?? '') !== filters.region) return false;
    return passesNodeFilters(f, filters) && passesKind(f, filters) && passesProduces(f, filters);
  });
}

/** Resource-node-only filters (resource / purity / miner status). */
function passesNodeFilters(f: MapFeature, filters: WorldFilters): boolean {
  if (f.type !== 'resource_node') return true;
  if (filters.resource !== 'all' && f.meta.resource !== filters.resource) return false;
  if (filters.purity !== 'all' && f.meta.purity !== filters.purity) return false;
  if (filters.nodeStatus === 'free' && f.occupied === true) return false;
  if (filters.nodeStatus === 'occupied' && f.occupied !== true) return false;
  return true;
}

/** Pickup-only kind filter. */
function passesKind(f: MapFeature, filters: WorldFilters): boolean {
  if (filters.kind === 'all' || !PICKUP_TYPES.has(f.type)) return true;
  return f.meta.kind === filters.kind;
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
