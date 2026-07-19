/**
 * DOM-level regression test: the WorldMap must actually place marker icons in
 * the Leaflet marker pane for live-shaped FRM data with default (fresh)
 * localStorage. Guards the full chain: default layer visibility → filters →
 * featureLayerId mapping → featureIcon markup.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import WorldMap from '../pages/WorldMap';
import type { WorldSnapshot } from '../types/world';

const WORLD: WorldSnapshot = {
  generated_at: '2026-07-18T00:00:00Z',
  source: 'frm',
  players: [],
  features: [
    {
      id: 'iron-ore-1',
      type: 'resource_node',
      name: 'Iron Ore (Normal)',
      position: { x: 100_000, y: -50_000, z: 0 },
      meta: { resource: 'iron-ore', purity: 'normal' },
      collected: null,
      occupied: false,
    },
    {
      id: 'artifact-1',
      type: 'artifact',
      name: 'Somersloop',
      position: { x: 0, y: 0, z: 0 },
      meta: { kind: 'somersloop' },
      collected: false,
      occupied: null,
    },
    {
      id: 'factory-1',
      type: 'factory',
      name: 'Smelter',
      position: { x: 5_000, y: 5_000, z: 0 },
      meta: { kind: 'smelter', class_name: 'Build_SmelterMk1_C', rotation: 0, status: 'caution' },
      collected: null,
      occupied: null,
    },
  ],
  belts: [],
  cables: [],
  pipes: [],
};

function renderMap() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity, retry: false } },
  });
  queryClient.setQueryData(['world', 'snapshot'], WORLD);
  queryClient.setQueryData(['world', 'markers'], []);
  queryClient.setQueryData(['scim', 'static-layers'], {});
  queryClient.setQueryData(['scim', 'building-models'], {});
  return render(
    <QueryClientProvider client={queryClient}>
      <WorldMap />
    </QueryClientProvider>,
  );
}

describe('WorldMap marker rendering', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders live feature pins with their icons by default', () => {
    const { container } = renderMap();
    const markerPane = container.querySelector('.leaflet-marker-pane');
    expect(markerPane).not.toBeNull();
    // All three live features are visible with default layers.
    expect(markerPane!.children.length).toBe(3);
    // The iron node pin embeds the vendored SCIM resource icon.
    expect(container.querySelector('img[src*="IconDesc_iron_new_256"]')).not.toBeNull();
    // The somersloop pin embeds the SCIM artifact icon.
    expect(container.querySelector('img[src*="Wat_1_256"], img[src*="Wat_2_256"]')).not.toBeNull();
  });
});
