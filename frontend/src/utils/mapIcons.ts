import { divIcon, type DivIcon } from 'leaflet';
import type { FeatureType, MapFeature } from '../types/world';

/**
 * Leaflet marker icons for world-map features.
 *
 * Each feature type gets a distinct glyph on a colored badge (a real icon, not a
 * plain dot). Resource nodes are colored by **purity** — impure red, normal
 * yellow, pure green — so deposit quality reads at a glance.
 *
 * Real game art can replace the SVG glyphs with no code change: drop a PNG at
 * ``/assets/icons/<type>.png`` (see {@link ICON_ASSET_BASE}) and it is used
 * automatically, falling back to the built-in glyph when the file is absent.
 */

/** Purity → badge color (red / yellow / green). */
export const PURITY_COLOR: Record<string, string> = {
  impure: '#e0524d',
  normal: '#e0b000',
  pure: '#28a745',
};

/** Per-type badge color (used for the icon and the legend toggles). */
export const FEATURE_COLOR: Record<FeatureType, string> = {
  factory: '#3987e5',
  resource_node: '#199e70',
  resource_well: '#00a3b4',
  geyser: '#7bb662',
  power_plant: '#c98500',
  train_station: '#9085e9',
  drone_port: '#d55181',
  truck_station: '#d95926',
  artifact: '#9085e9',
  collectible: '#008300',
  wreck: '#e66767',
};

/** Filled 24×24 SVG glyph (path data) per feature type. */
const GLYPH: Record<FeatureType, string> = {
  factory: 'M4 21V8l8-5 8 5v13h-6v-5h-4v5z',
  resource_node: 'M12 2l5 6-5 14-5-14z',
  resource_well: 'M12 2C12 2 5 10 5 15a7 7 0 0014 0C19 10 12 2 12 2z',
  geyser: 'M12 2c1 4 5 6 5 10a5 5 0 01-10 0c0-4 4-6 5-10z',
  power_plant: 'M13 2 4 14h6l-1 8 9-12h-6z',
  train_station:
    'M5 4h14a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2zM8 17a1.5 1.5 0 100 3 1.5 1.5 0 000-3zm8 0a1.5 1.5 0 100 3 1.5 1.5 0 000-3z',
  drone_port: 'M2 3 22 12 2 21 6 12z',
  truck_station:
    'M1 6h12v9H1zM13 9h4l4 3.5V15h-8zM5 19a2 2 0 100-4 2 2 0 000 4zm12 0a2 2 0 100-4 2 2 0 000 4z',
  artifact: 'M12 2l2.9 6.3 6.9.6-5.2 4.6 1.6 6.8L12 17l-6.2 3.9 1.6-6.8L2.2 9.5l6.9-.6z',
  collectible: 'M20 4C9 4 4 11 4 20c9 0 16-5 16-16z',
  wreck: 'M12 2l2.2 5.5L20 5l-2.5 5.5L23 13l-5.8.5L18 19l-6-3-6 3 .8-5.5L1 13l5.5-2.5L4 5l5.8 2.5z',
};

/** Base path where optional game-art PNGs (``<type>.png``) may be placed. */
export const ICON_ASSET_BASE = '/assets/icons';

/**
 * Feature types for which a real game-art PNG has been provided under
 * {@link ICON_ASSET_BASE}. Empty until art is added; listing a type here makes
 * its markers use the PNG instead of the SVG glyph.
 */
const ASSET_TYPES: ReadonlySet<FeatureType> = new Set();

const SIZE = 26;

/** Resolve a feature's badge color (purity for nodes, else the type color). */
function colorFor(feature: MapFeature): string {
  if (feature.type === 'resource_node') {
    const purity = String(feature.meta.purity ?? 'normal');
    return PURITY_COLOR[purity] ?? FEATURE_COLOR.resource_node;
  }
  return FEATURE_COLOR[feature.type];
}

function badgeHtml(feature: MapFeature): string {
  const dim = feature.collected === true || feature.occupied === true;
  const opacity = dim ? 0.5 : 1;
  const inner = ASSET_TYPES.has(feature.type)
    ? `<img src="${ICON_ASSET_BASE}/${feature.type}.png" width="16" height="16" alt="" />`
    : `<svg viewBox="0 0 24 24" width="15" height="15" fill="#fff"><path d="${GLYPH[feature.type]}"/></svg>`;
  return (
    `<div style="width:${SIZE}px;height:${SIZE}px;border-radius:50%;` +
    `background:${colorFor(feature)};border:2px solid #10131a;` +
    `display:flex;align-items:center;justify-content:center;` +
    `box-shadow:0 1px 3px rgba(0,0,0,.55);opacity:${opacity}">${inner}</div>`
  );
}

/** Build the Leaflet {@link DivIcon} for a world feature. */
export function featureIcon(feature: MapFeature): DivIcon {
  return divIcon({
    className: '',
    iconSize: [SIZE, SIZE],
    iconAnchor: [SIZE / 2, SIZE / 2],
    popupAnchor: [0, -SIZE / 2],
    html: badgeHtml(feature),
  });
}
