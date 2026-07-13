import { describe, expect, it } from 'vitest';
import type { MapFeature } from '../types/world';
import { applyWorldFilters, metaOptions, type WorldFilters } from '../utils/worldFilters';

const feature = (partial: Partial<MapFeature>): MapFeature => ({
  id: 'x',
  type: 'factory',
  name: 'X',
  position: { x: 0, y: 0, z: 0 },
  meta: {},
  collected: null,
  occupied: null,
  ...partial,
});

const FEATURES: MapFeature[] = [
  feature({ id: 'f1', type: 'factory', name: 'Iron Works' }),
  feature({
    id: 'n1',
    type: 'resource_node',
    name: 'iron-ore (pure)',
    meta: { resource: 'iron-ore', purity: 'pure', region: 'Grass Fields' },
    occupied: false,
  }),
  feature({
    id: 'n2',
    type: 'resource_node',
    name: 'coal (normal)',
    meta: { resource: 'coal', purity: 'normal', region: 'Northern Forest' },
    occupied: true,
  }),
  feature({
    id: 'a1',
    type: 'artifact',
    name: 'Somersloop',
    meta: { region: 'Grass Fields' },
    collected: true,
  }),
];

const DEFAULTS: WorldFilters = {
  visible: {
    factory: true,
    resource_node: true,
    resource_well: true,
    geyser: true,
    power_plant: true,
    train_station: true,
    drone_port: true,
    truck_station: true,
    artifact: true,
    collectible: true,
    wreck: true,
  },
  search: '',
  hideCollected: false,
  resource: 'all',
  purity: 'all',
  nodeStatus: 'all',
  region: 'all',
};

describe('applyWorldFilters', () => {
  it('passes everything with defaults', () => {
    expect(applyWorldFilters(FEATURES, DEFAULTS)).toHaveLength(4);
  });

  it('filters nodes by resource, purity, and status', () => {
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, resource: 'iron-ore' }).map((f) => f.id))
      .toEqual(['f1', 'n1', 'a1']); // non-node types unaffected
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, purity: 'normal' }).map((f) => f.id))
      .toContain('n2');
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, nodeStatus: 'free' }).map((f) => f.id),
    ).not.toContain('n2');
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, nodeStatus: 'occupied' }).map((f) => f.id),
    ).not.toContain('n1');
  });

  it('region filter keeps only matching regions (regionless features hidden)', () => {
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, region: 'Grass Fields' }).map((f) => f.id),
    ).toEqual(['n1', 'a1']);
  });

  it('hideCollected drops collected pickups only', () => {
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, hideCollected: true }).map((f) => f.id),
    ).toEqual(['f1', 'n1', 'n2']);
  });

  it('search and layer visibility still apply', () => {
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, search: 'iron' })).toHaveLength(2);
    const noNodes = { ...DEFAULTS.visible, resource_node: false };
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, visible: noNodes })).toHaveLength(2);
  });
});

describe('metaOptions', () => {
  it('returns sorted distinct values', () => {
    expect(metaOptions(FEATURES, 'region')).toEqual(['Grass Fields', 'Northern Forest']);
    expect(metaOptions(FEATURES, 'resource')).toEqual(['coal', 'iron-ore']);
  });
});
