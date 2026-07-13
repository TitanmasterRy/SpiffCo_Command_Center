import { divIcon, type DivIcon } from 'leaflet';
import type { FeatureType, MapFeature } from '../types/world';
import { NODE_LIKE_TYPES, PICKUP_TYPES, pickupKind } from './worldFilters';

/**
 * Leaflet marker icons for world-map features.
 *
 * Features render as the real game icon inside a white disc ringed by a color:
 * node-like features (nodes / geysers / wells) are ringed by **purity** — impure
 * red, normal yellow, pure green — and everything else by its category color.
 * Features without a downloaded icon fall back to a colored badge with a built-in
 * SVG glyph.
 *
 * Game icons live under ``/assets/icons/{resource,pickup,type}/<key>.webp`` and
 * are fetched by ``scripts/fetch_game_icons.py``. The sets below list the keys
 * that have an icon file; add a key here after fetching a new icon.
 */

/** Purity → ring color (red / yellow / green). */
export const PURITY_COLOR: Record<string, string> = {
  impure: '#e0524d',
  normal: '#e0b000',
  pure: '#28a745',
};

/** Per-type ring/badge color. */
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

const ICON_BASE = '/assets/icons';
const RESOURCE_ICONS = new Set([
  'iron-ore', 'copper-ore', 'caterium-ore', 'coal', 'limestone', 'raw-quartz',
  'sulfur', 'bauxite', 'uranium', 'sam', 'crude-oil', 'water', 'nitrogen-gas',
]);
const PICKUP_ICONS = new Set([
  'somersloop', 'mercer-sphere', 'blue-power-slug', 'yellow-power-slug',
  'purple-power-slug', 'crash-site',
]);
const TYPE_ICONS = new Set<FeatureType>([
  'geyser', 'train_station', 'drone_port', 'truck_station', 'power_plant', 'factory',
]);

/** Filled 24×24 SVG glyph (path data) fallback per feature type. */
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

const SIZE = 26;

/** Ring/badge color for a feature (purity for node-like, else the type color). */
export function featureColor(feature: MapFeature): string {
  if (NODE_LIKE_TYPES.has(feature.type)) {
    const purity = String(feature.meta.purity ?? 'normal');
    return PURITY_COLOR[purity] ?? FEATURE_COLOR[feature.type];
  }
  return FEATURE_COLOR[feature.type];
}

/** Path to a feature's game icon, or null when none has been downloaded. */
function iconUrl(feature: MapFeature): string | null {
  if (PICKUP_TYPES.has(feature.type)) {
    const kind = pickupKind(feature);
    return PICKUP_ICONS.has(kind) ? `${ICON_BASE}/pickup/${kind}.webp` : null;
  }
  if (NODE_LIKE_TYPES.has(feature.type)) {
    const resource = String(feature.meta.resource ?? '');
    if (RESOURCE_ICONS.has(resource)) return `${ICON_BASE}/resource/${resource}.webp`;
    if (feature.type === 'geyser') return `${ICON_BASE}/type/geyser.webp`;
    return null;
  }
  return TYPE_ICONS.has(feature.type) ? `${ICON_BASE}/type/${feature.type}.webp` : null;
}

function badgeHtml(feature: MapFeature): string {
  const dim = feature.collected === true || feature.occupied === true;
  const opacity = dim ? 0.5 : 1;
  const ring = featureColor(feature);
  const url = iconUrl(feature);
  if (url) {
    // Game icon inside a light disc ringed by the feature/purity color.
    return (
      `<div style="width:${SIZE}px;height:${SIZE}px;border-radius:50%;` +
      `background:#eef2f7;border:3px solid ${ring};box-sizing:border-box;` +
      `display:flex;align-items:center;justify-content:center;` +
      `box-shadow:0 1px 3px rgba(0,0,0,.55);opacity:${opacity}">` +
      `<img src="${url}" width="16" height="16" style="object-fit:contain" alt="" /></div>`
    );
  }
  // Fallback: colored badge with a white SVG glyph.
  return (
    `<div style="width:${SIZE}px;height:${SIZE}px;border-radius:50%;` +
    `background:${ring};border:2px solid #10131a;box-sizing:border-box;` +
    `display:flex;align-items:center;justify-content:center;` +
    `box-shadow:0 1px 3px rgba(0,0,0,.55);opacity:${opacity}">` +
    `<svg viewBox="0 0 24 24" width="15" height="15" fill="#fff"><path d="${GLYPH[feature.type]}"/></svg></div>`
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

/** Small ``<img>`` markup for a pickup kind (for the filter toggles), or ''. */
export function pickupKindIconHtml(kind: string): string {
  return PICKUP_ICONS.has(kind)
    ? `<img src="${ICON_BASE}/pickup/${kind}.webp" width="16" height="16" alt="" />`
    : '';
}
