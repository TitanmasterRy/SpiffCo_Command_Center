import { describe, expect, it } from 'vitest';
import type { BlueprintSummary } from '../types/blueprint';
import {
  DEFAULT_BLUEPRINT_FILTERS,
  deriveFacets,
  deriveStats,
  filterBlueprints,
} from '../utils/blueprintFilters';

const bp = (partial: Partial<BlueprintSummary>): BlueprintSummary => ({
  id: 1,
  name: 'Blueprint',
  description: '',
  category: 'general',
  tags: [],
  favorite: false,
  created_at: '2026-07-13T00:00:00Z',
  updated_at: '2026-07-13T00:00:00Z',
  ...partial,
});

const LIB: BlueprintSummary[] = [
  bp({ id: 1, name: 'Iron Smelter', category: 'smelting', tags: ['iron', 'starter'], favorite: true }),
  bp({ id: 2, name: 'Coal Power', category: 'power', tags: ['coal'] }),
  bp({ id: 3, name: 'Copper Line', category: 'smelting', tags: ['copper'], description: 'wire' }),
];

describe('filterBlueprints', () => {
  it('passes everything with defaults', () => {
    expect(filterBlueprints(LIB, DEFAULT_BLUEPRINT_FILTERS)).toHaveLength(3);
  });

  it('filters by category, tag, favorite, and search', () => {
    expect(
      filterBlueprints(LIB, { ...DEFAULT_BLUEPRINT_FILTERS, category: 'smelting' }).map((b) => b.id),
    ).toEqual([1, 3]);
    expect(
      filterBlueprints(LIB, { ...DEFAULT_BLUEPRINT_FILTERS, tag: 'coal' }).map((b) => b.id),
    ).toEqual([2]);
    expect(
      filterBlueprints(LIB, { ...DEFAULT_BLUEPRINT_FILTERS, favoritesOnly: true }).map((b) => b.id),
    ).toEqual([1]);
    // Search matches name or description.
    expect(
      filterBlueprints(LIB, { ...DEFAULT_BLUEPRINT_FILTERS, search: 'wire' }).map((b) => b.id),
    ).toEqual([3]);
    expect(filterBlueprints(LIB, { ...DEFAULT_BLUEPRINT_FILTERS, search: 'copper' })).toHaveLength(1);
  });
});

describe('deriveFacets', () => {
  it('returns sorted distinct categories and tags', () => {
    const { categories, tags } = deriveFacets(LIB);
    expect(categories).toEqual(['power', 'smelting']);
    expect(tags).toEqual(['coal', 'copper', 'iron', 'starter']);
  });
});

describe('deriveStats', () => {
  it('counts totals, favorites, categories, and tags', () => {
    const stats = deriveStats(LIB);
    expect(stats.total).toBe(3);
    expect(stats.favorites).toBe(1);
    expect(stats.by_category).toEqual({ smelting: 2, power: 1 });
    expect(stats.by_tag.iron).toBe(1);
  });
});
