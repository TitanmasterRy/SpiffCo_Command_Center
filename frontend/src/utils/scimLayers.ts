import scimLayersJson from '../data/scimLayers.json';
import type { ScimCategory, ScimLayer } from '../types/scim';
import type { MapFeature } from '../types/world';

/**
 * SCIM layer taxonomy: category tree, per-layer lookup, and the mapping from
 * our live FRM world features onto SCIM layer ids (the unit of filtering on
 * the world map, exactly as on satisfactory-calculator.com).
 */

export const SCIM_CATEGORIES: ScimCategory[] = (
  scimLayersJson as { categories: ScimCategory[] }
).categories;

/** Every SCIM layer by id. */
export const SCIM_LAYER_BY_ID: ReadonlyMap<string, ScimLayer> = new Map(
  SCIM_CATEGORIES.flatMap((category) =>
    category.groups.flatMap((group) => group.layers.map((layer) => [layer.id, layer] as const)),
  ),
);

/**
 * Our pickup `meta.kind` slugs → SCIM layer id. Includes aliases because the
 * simulation and FRM name slugs differently (e.g. `power-slug-green` vs the
 * FRM-derived `blue-power-slug` — SCIM's "green" slugs are the in-game blue
 * ones).
 */
const PICKUP_LAYER_BY_KIND: Record<string, string> = {
  'blue-power-slug': 'greenSlugs',
  'green-power-slug': 'greenSlugs',
  'power-slug-green': 'greenSlugs',
  'yellow-power-slug': 'yellowSlugs',
  'power-slug-yellow': 'yellowSlugs',
  'purple-power-slug': 'purpleSlugs',
  'power-slug-purple': 'purpleSlugs',
  somersloop: 'somersloops',
  'mercer-sphere': 'mercerSpheres',
  'crash-site': 'hardDrives',
  paleberry: 'paleBerry',
  'pale-berry': 'paleBerry',
  'beryl-nut': 'berylNut',
  'bacon-agaric': 'baconAgaric',
};

/** `<kind>:<resource>:<purity>` (nodes/wells) or `geyser:<purity>` → layer id. */
const MATCH_LAYER: ReadonlyMap<string, string> = new Map(
  [...SCIM_LAYER_BY_ID.values()].flatMap((layer) => {
    const match = layer.match;
    if (!match) return [];
    if (match.kind === 'pickup') return []; // handled via PICKUP_LAYER_BY_KIND
    const key =
      match.kind === 'geyser'
        ? `geyser:${match.purity}`
        : `${match.kind}:${match.resource}:${match.purity}`;
    return [[key, layer.id] as const];
  }),
);

/**
 * The SCIM layer id a live feature belongs to, or a `live:<type>` fallback for
 * features SCIM has no layer for (factories, stations, unknown kinds, …).
 */
export function featureLayerId(feature: MapFeature): string {
  const purity = String(feature.meta.purity ?? 'normal');
  switch (feature.type) {
    case 'resource_node': {
      const id = MATCH_LAYER.get(`node:${String(feature.meta.resource ?? '')}:${purity}`);
      if (id) return id;
      break;
    }
    case 'resource_well': {
      const id = MATCH_LAYER.get(`well:${String(feature.meta.resource ?? '')}:${purity}`);
      if (id) return id;
      break;
    }
    case 'geyser': {
      const id = MATCH_LAYER.get(`geyser:${purity}`);
      if (id) return id;
      break;
    }
    case 'artifact':
    case 'collectible':
    case 'wreck': {
      const id = PICKUP_LAYER_BY_KIND[String(feature.meta.kind ?? '')];
      if (id) return id;
      break;
    }
    default:
      break;
  }
  return `live:${feature.type}`;
}

/** The SCIM layer for a live feature, if it maps onto one. */
export function featureScimLayer(feature: MapFeature): ScimLayer | undefined {
  return SCIM_LAYER_BY_ID.get(featureLayerId(feature));
}
