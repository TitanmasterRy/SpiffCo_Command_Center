import { describe, expect, it } from 'vitest';
import type { MapFeature } from '../types/world';
import {
  COLLECTED_OPACITY,
  FEATURE_COLOR,
  featureIcon,
  PURITY_COLOR,
  swatchColor,
} from '../utils/mapIcons';
import { SCIM_LAYER_BY_ID } from '../utils/scimLayers';

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

const html = (f: MapFeature): string => String(featureIcon(f).options.html);

describe('featureIcon (SCIM pin style)', () => {
  it('fills resource-node pins red/orange/green by purity (SCIM palette)', () => {
    for (const purity of ['impure', 'normal', 'pure'] as const) {
      expect(
        html(feature({ type: 'resource_node', meta: { resource: 'iron-ore', purity } })),
      ).toContain(PURITY_COLOR[purity]);
    }
  });

  it('rings node pins with the SCIM resource color', () => {
    const ironLayer = SCIM_LAYER_BY_ID.get('ironPure');
    expect(ironLayer?.outsideColor).toBeTruthy();
    expect(
      html(feature({ type: 'resource_node', meta: { resource: 'iron-ore', purity: 'pure' } })),
    ).toContain(String(ironLayer?.outsideColor));
  });

  it('uses SCIM layer colors and icon for mapped pickups', () => {
    const sloop = SCIM_LAYER_BY_ID.get('somersloops');
    const markup = html(feature({ type: 'artifact', meta: { kind: 'somersloop' } }));
    expect(markup).toContain(String(sloop?.outsideColor));
    expect(markup).toContain(String(sloop?.icon));
  });

  it('rings a painted building with its swatch color instead of the type color', () => {
    const painted = feature({ type: 'factory', meta: { kind: 'miner', color: '#e61a1a' } });
    const markup = html(painted);
    // The swatch color paints the ring/anchor; the default factory color does not.
    expect(markup).toContain('#e61a1a');
    expect(markup).not.toContain(FEATURE_COLOR.factory);
    // Unpainted buildings fall back to the per-type color.
    expect(html(feature({ type: 'factory', meta: {} }))).toContain(FEATURE_COLOR.factory);
  });

  it('swatchColor validates the hex and ignores anything else', () => {
    expect(swatchColor(feature({ meta: { color: '#1e88e5' } }))).toBe('#1e88e5');
    expect(swatchColor(feature({ meta: { color: 'blue' } }))).toBeNull();
    expect(swatchColor(feature({ meta: {} }))).toBeNull();
  });

  it('dims collected pickups and occupied nodes to SCIM opacity', () => {
    expect(html(feature({ type: 'artifact', collected: true }))).toContain(
      `opacity:${COLLECTED_OPACITY}`,
    );
    expect(html(feature({ type: 'resource_node', occupied: true }))).toContain(
      `opacity:${COLLECTED_OPACITY}`,
    );
    expect(html(feature({ type: 'resource_node', occupied: false }))).toContain('opacity:1');
  });
});
