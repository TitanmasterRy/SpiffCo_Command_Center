import type { BlueprintStats, BlueprintSummary } from '../types/blueprint';

/**
 * Client-side blueprint filtering, facet extraction, and stat derivation. The
 * page fetches the full library once and filters locally for snappy UX; these
 * pure helpers keep that logic testable.
 */

export interface BlueprintFilters {
  /** Category id, or 'all'. */
  category: string;
  /** Tag, or 'all'. */
  tag: string;
  /** Only favorites when true. */
  favoritesOnly: boolean;
  /** Case-insensitive name/description substring; '' disables. */
  search: string;
}

export const DEFAULT_BLUEPRINT_FILTERS: BlueprintFilters = {
  category: 'all',
  tag: 'all',
  favoritesOnly: false,
  search: '',
};

/** Apply all filters to a blueprint list. */
export function filterBlueprints(
  blueprints: BlueprintSummary[],
  filters: BlueprintFilters,
): BlueprintSummary[] {
  const q = filters.search.trim().toLowerCase();
  return blueprints.filter((b) => {
    if (filters.category !== 'all' && b.category !== filters.category) return false;
    if (filters.tag !== 'all' && !b.tags.includes(filters.tag)) return false;
    if (filters.favoritesOnly && !b.favorite) return false;
    if (q && !b.name.toLowerCase().includes(q) && !b.description.toLowerCase().includes(q)) {
      return false;
    }
    return true;
  });
}

/** Sorted distinct categories and tags across the library (for filter options). */
export function deriveFacets(blueprints: BlueprintSummary[]): {
  categories: string[];
  tags: string[];
} {
  const categories = new Set<string>();
  const tags = new Set<string>();
  for (const b of blueprints) {
    categories.add(b.category);
    for (const t of b.tags) tags.add(t);
  }
  return {
    categories: [...categories].sort(),
    tags: [...tags].sort(),
  };
}

/** Derive library statistics from the loaded summaries. */
export function deriveStats(blueprints: BlueprintSummary[]): BlueprintStats {
  const byCategory: Record<string, number> = {};
  const byTag: Record<string, number> = {};
  let favorites = 0;
  for (const b of blueprints) {
    byCategory[b.category] = (byCategory[b.category] ?? 0) + 1;
    if (b.favorite) favorites += 1;
    for (const t of b.tags) byTag[t] = (byTag[t] ?? 0) + 1;
  }
  return { total: blueprints.length, favorites, by_category: byCategory, by_tag: byTag };
}
