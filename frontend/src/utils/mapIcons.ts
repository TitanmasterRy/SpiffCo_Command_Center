import { divIcon, type DivIcon } from 'leaflet';
import type { ScimLayer } from '../types/scim';
import type { FeatureType, MapFeature } from '../types/world';
import { featureScimLayer } from './scimLayers';
import { NODE_LIKE_TYPES, PICKUP_TYPES, pickupKind } from './worldFilters';

/**
 * Leaflet marker icons for world-map features, drawn in SCIM's visual style
 * (satisfactory-calculator.com Interactive Map): a pin whose head is a circle
 * filled with the layer's *inside* color (purity for nodes) and ringed by its
 * *outside* color (resource color), the layer icon on top, and a thin anchor
 * line down to a dot at the exact world position. Collected pickups and
 * occupied nodes render at SCIM's collected opacity (0.3).
 *
 * Features that map onto a vendored SCIM layer (`utils/scimLayers.ts`) use its
 * colors and icon; everything else (factories, stations, …) uses the same pin
 * with our per-type color and local icon or a built-in SVG glyph.
 */

/** Purity → fill color (SCIM's palette: red / orange / green). */
export const PURITY_COLOR: Record<string, string> = {
  impure: '#d23430',
  normal: '#f26418',
  pure: '#80b139',
};

/** Per-type ring color for features without a SCIM layer. */
export const FEATURE_COLOR: Record<FeatureType, string> = {
  factory: '#3987e5',
  resource_node: '#199e70',
  resource_well: '#00a3b4',
  geyser: '#f8d450',
  power_plant: '#c98500',
  train_station: '#9085e9',
  drone_port: '#d55181',
  truck_station: '#d95926',
  artifact: '#9085e9',
  collectible: '#008300',
  wreck: '#e66767',
};

/** SCIM dims collected markers to this opacity. */
export const COLLECTED_OPACITY = 0.3;

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

/**
 * Marker scale factor for a zoom level (map runs zoom 3–12 under the SCIM
 * projection), so pins shrink when the whole map is visible and grow close-up.
 * Stepped, not continuous, so icons only re-render at bucket boundaries.
 */
export function iconScale(zoom: number): number {
  if (zoom < 4) return 0.55;
  if (zoom < 5) return 0.7;
  if (zoom < 6) return 0.85;
  if (zoom < 7.5) return 1;
  return 1.2;
}

/** Ring/badge color for a feature (purity for node-like, else the type color). */
export function featureColor(feature: MapFeature): string {
  if (NODE_LIKE_TYPES.has(feature.type)) {
    const purity = String(feature.meta.purity ?? 'normal');
    return PURITY_COLOR[purity] ?? FEATURE_COLOR[feature.type];
  }
  return FEATURE_COLOR[feature.type];
}

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;

/**
 * The building's in-game paint-swatch color (`meta.color`), or null. Set by the
 * backend for miners, extractors, and other painted buildings; when present it
 * overrides the default per-type ring color so the pin matches the swatch.
 */
export function swatchColor(feature: MapFeature): string | null {
  const color = feature.meta.color;
  return typeof color === 'string' && HEX_COLOR.test(color) ? color : null;
}

/** Path to a feature's local game icon, or null when none has been downloaded. */
function localIconUrl(feature: MapFeature): string | null {
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

/** Base pin dimensions at scale 1 (px). */
const PIN_W = 36;
const PIN_H = 52;
const HEAD_R = 14;

interface PinSpec {
  outsideColor: string;
  insideColor: string;
  /** Image URL drawn over the head (preferred). */
  iconUrl?: string | null;
  /** 24×24 SVG path drawn over the head when no image icon exists. */
  glyph?: string;
  opacity?: number;
}

/**
 * SCIM-style pin markup: head circle + anchor line + position dot as inline
 * SVG, with the icon image (drawn at 1.4× head radius, as SCIM does) overlaid.
 * Sizing MUST be inline: Tailwind preflight (`img{height:auto}`) and Leaflet
 * (`img{max-width:none}`) both override width/height attributes. The overlay
 * also MUST set `z-index` above the pin SVG: Leaflet's stylesheet gives inline
 * SVGs `z-index:200`, so without this the head disc paints over the icon and
 * every marker reads as a plain colored circle.
 */
function pinHtml(spec: PinSpec, scale: number): string {
  const w = Math.round(PIN_W * scale);
  const h = Math.round(PIN_H * scale);
  const cx = w / 2;
  const r = HEAD_R * scale;
  const cy = r + 2;
  // Never let the icon shrink below a legible size, even when the pin itself
  // keeps scaling down at low zoom (it was reading as a plain colored dot).
  const icon = Math.max(16, Math.round(r * 1.4));
  const opacity = spec.opacity ?? 1;
  const image = spec.iconUrl
    ? `<img src="${spec.iconUrl}" alt="" style="position:absolute;z-index:400;left:${Math.round(cx - icon / 2)}px;top:${Math.round(cy - icon / 2)}px;width:${icon}px;height:${icon}px;min-width:0;object-fit:contain;display:block;filter:drop-shadow(0 1px 1px rgba(0,0,0,.5))" />`
    : spec.glyph
      ? `<svg viewBox="0 0 24 24" style="position:absolute;z-index:400;left:${Math.round(cx - icon / 2)}px;top:${Math.round(cy - icon / 2)}px;width:${icon}px;height:${icon}px;fill:#fff"><path d="${spec.glyph}"/></svg>`
      : '';
  return (
    `<div style="position:relative;width:${w}px;height:${h}px;opacity:${opacity}">` +
    `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="position:absolute;inset:0;overflow:visible">` +
    `<line x1="${cx}" y1="${h - 3}" x2="${cx}" y2="${cy + r}" stroke="${spec.outsideColor}" stroke-width="${Math.max(1.5, 2 * scale)}"/>` +
    `<circle cx="${cx}" cy="${h - 3}" r="${Math.max(2, 2.5 * scale)}" fill="${spec.outsideColor}"/>` +
    `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${spec.insideColor}" stroke="${spec.outsideColor}" stroke-width="${Math.max(2, 3 * scale)}" style="filter:drop-shadow(0 1px 2px rgba(0,0,0,.55))"/>` +
    `</svg>${image}</div>`
  );
}

function pinIcon(spec: PinSpec, scale: number): DivIcon {
  const w = Math.round(PIN_W * scale);
  const h = Math.round(PIN_H * scale);
  return divIcon({
    className: '',
    iconSize: [w, h],
    // The dot at the bottom of the anchor line marks the world position.
    iconAnchor: [w / 2, h - 3],
    popupAnchor: [0, -h],
    html: pinHtml(spec, scale),
  });
}

/** Build the Leaflet {@link DivIcon} for a live world feature at a given scale. */
export function featureIcon(feature: MapFeature, scale = 1): DivIcon {
  const dim = feature.collected === true || feature.occupied === true;
  const opacity = dim ? COLLECTED_OPACITY : 1;
  // A painted building's swatch color wins for the pin ring / anchor when set.
  const swatch = swatchColor(feature);
  const layer = featureScimLayer(feature);
  if (layer?.outsideColor && layer.insideColor) {
    return pinIcon(
      {
        outsideColor: swatch ?? layer.outsideColor,
        insideColor: layer.insideColor,
        iconUrl: layer.icon ?? localIconUrl(feature),
        glyph: GLYPH[feature.type],
        opacity,
      },
      scale,
    );
  }
  const nodeLike = NODE_LIKE_TYPES.has(feature.type);
  return pinIcon(
    {
      outsideColor: swatch ?? (nodeLike ? featureColor(feature) : FEATURE_COLOR[feature.type]),
      insideColor: nodeLike ? featureColor(feature) : '#ffffff',
      iconUrl: localIconUrl(feature),
      glyph: GLYPH[feature.type],
      opacity,
    },
    scale,
  );
}

/** Pin icon for a vendored static SCIM layer marker (berries, nuts, …). */
export function scimLayerIcon(layer: ScimLayer, scale = 1): DivIcon {
  return pinIcon(
    {
      outsideColor: layer.outsideColor ?? '#666666',
      insideColor: layer.insideColor ?? '#ffffff',
      iconUrl: layer.icon,
    },
    scale,
  );
}
