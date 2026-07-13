import { describe, expect, it } from 'vitest';
import type { MapFeature } from '../types/world';
import { featureIcon, PURITY_COLOR } from '../utils/mapIcons';

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

describe('featureIcon', () => {
  it('colors resource nodes red/yellow/green by purity', () => {
    expect(html(feature({ type: 'resource_node', meta: { purity: 'impure' } }))).toContain(
      PURITY_COLOR.impure,
    );
    expect(html(feature({ type: 'resource_node', meta: { purity: 'normal' } }))).toContain(
      PURITY_COLOR.normal,
    );
    expect(html(feature({ type: 'resource_node', meta: { purity: 'pure' } }))).toContain(
      PURITY_COLOR.pure,
    );
  });

  it('dims collected pickups and occupied nodes', () => {
    expect(html(feature({ type: 'artifact', collected: true }))).toContain('opacity:0.5');
    expect(html(feature({ type: 'resource_node', occupied: true }))).toContain('opacity:0.5');
    expect(html(feature({ type: 'resource_node', occupied: false }))).toContain('opacity:1');
  });
});
