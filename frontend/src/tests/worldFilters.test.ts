import { describe, expect, it } from 'vitest';
import type { MapFeature } from '../types/world';
import { featureLayerId } from '../utils/scimLayers';
import {
  applyWorldFilters,
  metaOptions,
  producesOptions,
  type WorldFilters,
} from '../utils/worldFilters';

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
  feature({ id: 'f1', type: 'factory', name: 'Iron Works', meta: { produces: 'Iron Plate, Screw' } }),
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
    meta: { region: 'Grass Fields', kind: 'somersloop' },
    collected: true,
  }),
];

// Every layer that appears in the fixture set, enabled.
const ALL_ON: Record<string, boolean> = {
  'live:factory': true,
  ironPure: true,
  coalNormal: true,
  somersloops: true,
};

const DEFAULTS: WorldFilters = {
  activeLayers: ALL_ON,
  search: '',
  hideCollected: false,
  nodeStatus: 'all',
  produces: 'all',
  region: 'all',
};

describe('featureLayerId', () => {
  it('maps nodes onto SCIM resource+purity layers', () => {
    expect(featureLayerId(FEATURES[1])).toBe('ironPure');
    expect(featureLayerId(FEATURES[2])).toBe('coalNormal');
  });

  it('maps pickups by kind, including slug aliases', () => {
    expect(featureLayerId(FEATURES[3])).toBe('somersloops');
    expect(
      featureLayerId(feature({ type: 'artifact', meta: { kind: 'blue-power-slug' } })),
    ).toBe('greenSlugs'); // SCIM calls the in-game blue slugs "green"
    expect(
      featureLayerId(feature({ type: 'artifact', meta: { kind: 'power-slug-green' } })),
    ).toBe('greenSlugs');
    expect(featureLayerId(feature({ type: 'wreck', meta: { kind: 'crash-site' } }))).toBe(
      'hardDrives',
    );
    expect(
      featureLayerId(feature({ type: 'collectible', meta: { kind: 'paleberry' } })),
    ).toBe('paleBerry');
  });

  it('falls back to live:<type> for unmapped features', () => {
    expect(featureLayerId(FEATURES[0])).toBe('live:factory');
    expect(featureLayerId(feature({ type: 'artifact', meta: { kind: 'mystery' } }))).toBe(
      'live:artifact',
    );
  });

  it('maps wells and geysers onto their SCIM layers', () => {
    expect(
      featureLayerId(
        feature({ type: 'resource_well', meta: { resource: 'nitrogen-gas', purity: 'pure' } }),
      ),
    ).toBe('nitrogenGasWellPure');
    expect(featureLayerId(feature({ type: 'geyser', meta: { purity: 'impure' } }))).toBe(
      'geyserImpure',
    );
  });
});

describe('applyWorldFilters', () => {
  it('passes everything when all layers are on', () => {
    expect(applyWorldFilters(FEATURES, DEFAULTS)).toHaveLength(4);
  });

  it('shows only features whose layer is enabled', () => {
    const onlyIron = applyWorldFilters(FEATURES, {
      ...DEFAULTS,
      activeLayers: { ironPure: true },
    });
    expect(onlyIron.map((f) => f.id)).toEqual(['n1']);
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, activeLayers: {} })).toHaveLength(0);
  });

  it('filters nodes by miner status', () => {
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

  it('search still applies', () => {
    expect(applyWorldFilters(FEATURES, { ...DEFAULTS, search: 'iron' })).toHaveLength(2);
  });

  it('produces filter constrains only factories', () => {
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, produces: 'Iron Plate' }).map((f) => f.id),
    ).toContain('f1');
    expect(
      applyWorldFilters(FEATURES, { ...DEFAULTS, produces: 'Plastic' }).map((f) => f.id),
    ).not.toContain('f1'); // factory not producing it is dropped
  });
});

describe('producesOptions', () => {
  it('returns sorted distinct factory output items', () => {
    expect(producesOptions(FEATURES)).toEqual(['Iron Plate', 'Screw']);
  });
});

describe('metaOptions', () => {
  it('returns sorted distinct values', () => {
    expect(metaOptions(FEATURES, 'region')).toEqual(['Grass Fields', 'Northern Forest']);
    expect(metaOptions(FEATURES, 'resource')).toEqual(['coal', 'iron-ore']);
  });
});
