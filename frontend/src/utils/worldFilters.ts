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
  /**
   * Keep only features whose meta.region matches ('all' disables).
   * Features without a region (built infrastructure) are hidden while a
   * specific region is selected — the view answers "what does this region offer".
   */
  region: string;
}

/** Apply all map filters; single source of truth for the WorldMap view. */
export function applyWorldFilters(features: MapFeature[], filters: WorldFilters): MapFeature[] {
  const query = filters.search.trim().toLowerCase();
  return features.filter((f) => {
    if (!filters.visible[f.type]) return false;
    if (filters.hideCollected && f.collected === true) return false;
    if (query && !f.name.toLowerCase().includes(query)) return false;
    if (f.type === 'resource_node') {
      if (filters.resource !== 'all' && f.meta.resource !== filters.resource) return false;
      if (filters.purity !== 'all' && f.meta.purity !== filters.purity) return false;
      if (filters.nodeStatus === 'free' && f.occupied === true) return false;
      if (filters.nodeStatus === 'occupied' && f.occupied !== true) return false;
    }
    if (filters.region !== 'all' && String(f.meta.region ?? '') !== filters.region) return false;
    return true;
  });
}

/** Distinct, sorted values of a meta key across features (for filter options). */
export function metaOptions(features: MapFeature[], key: string): string[] {
  return [...new Set(features.map((f) => String(f.meta[key] ?? '')).filter(Boolean))].sort();
}
