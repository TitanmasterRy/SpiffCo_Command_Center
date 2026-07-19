import { CRS, type LeafletMouseEvent, type Path } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Fragment, useMemo, useState } from 'react';
import {
  Circle,
  CircleMarker,
  ImageOverlay,
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
  useMapEvents,
} from 'react-leaflet';
import { useQuery } from '@tanstack/react-query';
import { BuildingPanel } from '../components/BuildingPanel';
import { Card } from '../components/Card';
import { MapLayerPanel, type LayerCounts, type LiveLayerEntry } from '../components/MapLayerPanel';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useWorld, useMarkers } from '../hooks/useWorld';
import type { ScimStaticLayers } from '../types/scim';
import type { FeatureType } from '../types/world';
import { buildingOutline, type BuildingModels } from '../utils/buildingOutline';
import {
  fromLatLng,
  MAP_BOUNDS,
  MAP_CENTER,
  MAP_IMAGE_BOUNDS,
  MAP_IMAGE_URL,
  MAX_NATIVE_ZOOM,
  MAX_ZOOM,
  MIN_TILE_ZOOM,
  scimTileUrl,
  toLatLng,
} from '../utils/mapCoords';
import { FEATURE_COLOR, featureIcon, iconScale, PURITY_COLOR, scimLayerIcon } from '../utils/mapIcons';
import { SCIM_CATEGORIES, SCIM_LAYER_BY_ID, featureLayerId } from '../utils/scimLayers';
import { applyWorldFilters, metaOptions, producesOptions } from '../utils/worldFilters';

/** Legend labels per feature type; colors live in {@link FEATURE_COLOR}. */
const FEATURE_LABEL: Record<FeatureType, string> = {
  factory: 'Factories',
  resource_node: 'Resource nodes',
  resource_well: 'Resource wells',
  geyser: 'Geysers',
  power_plant: 'Power plants',
  train_station: 'Train stations',
  drone_port: 'Drone ports',
  truck_station: 'Truck stations',
  artifact: 'Artifacts',
  collectible: 'Food & consumables',
  wreck: 'Crash sites',
};
const PLAYER_COLOR = '#e66767';
const MARKER_COLOR = '#94a3b8';

type BaseLayerChoice = 'game' | 'realistic' | 'offline' | 'none';

const BASE_LAYER_OPTIONS: { value: BaseLayerChoice; label: string }[] = [
  { value: 'game', label: 'Game map' },
  { value: 'realistic', label: 'Realistic' },
  { value: 'offline', label: 'Offline image' },
  { value: 'none', label: 'None' },
];

/** SCIM's circle styling for the simple static point layers. */
const STATIC_CIRCLE_STYLE: Record<string, { radius: number; color: string }> = {
  sporeFlowers: { radius: 0.4, color: '#41a5a3' },
  pillars: { radius: 0.6, color: '#bee597' },
  smallRocks: { radius: 0.1, color: '#555555' },
  largeRocks: { radius: 0.3, color: '#555555' },
};
/** Static layers rendered as SCIM pins (with the layer icon). */
const STATIC_PIN_LAYERS = ['paleBerry', 'berylNut', 'baconAgaric'] as const;

const VIEW_STORAGE_KEY = 'spiffco.map.view.v2';
const DEFAULT_VIEW = { center: MAP_CENTER, zoom: 3 };

/** Last-used map view (center/zoom) from localStorage, or the default. */
function loadView(): { center: [number, number]; zoom: number } {
  try {
    const raw = localStorage.getItem(VIEW_STORAGE_KEY);
    if (!raw) return DEFAULT_VIEW;
    const v = JSON.parse(raw) as { center: [number, number]; zoom: number };
    if (
      Array.isArray(v.center) &&
      v.center.length === 2 &&
      v.center.every((n) => Number.isFinite(n)) &&
      Number.isFinite(v.zoom)
    ) {
      return v;
    }
  } catch {
    // Fall through to the default on malformed storage.
  }
  return DEFAULT_VIEW;
}

/**
 * Persists the view across visits and reports zoom changes (used to scale
 * marker icons with zoom, as SCIM does).
 */
function ViewTracker({ onZoom }: { onZoom: (zoom: number) => void }) {
  const map = useMapEvents({
    zoomend: () => onZoom(map.getZoom()),
    moveend: () => {
      const c = map.getCenter();
      localStorage.setItem(
        VIEW_STORAGE_KEY,
        JSON.stringify({ center: [c.lat, c.lng], zoom: map.getZoom() }),
      );
    },
  });
  return null;
}

function AddMarkerOnClick({ onPick }: { onPick: (e: LeafletMouseEvent) => void }) {
  useMapEvents({ contextmenu: onPick });
  return null;
}

/** Reports the cursor's game-world coordinates (cm) as the mouse moves. */
function CursorTracker({ onMove }: { onMove: (pos: { x: number; y: number } | null) => void }) {
  useMapEvents({
    mousemove: (e) => {
      const p = fromLatLng(e.latlng.lat, e.latlng.lng);
      onMove({ x: p.x, y: p.y });
    },
    mouseout: () => onMove(null),
  });
  return null;
}

interface SelectFilterProps {
  label: string;
  /** Emoji/icon shown before the label. */
  icon: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

/** Labeled dropdown used in the map toolbar; first option should be 'all'. */
function SelectFilter({ label, icon, value, options, onChange }: SelectFilterProps) {
  const active = value !== 'all';
  return (
    <label
      className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs ${
        active
          ? 'border-accent/50 bg-accent/10 text-accent'
          : 'border-surface-border bg-surface-raised text-slate-400'
      }`}
    >
      <span aria-hidden>{icon}</span>
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border-0 bg-transparent py-0.5 text-xs text-slate-200 focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-surface text-slate-200">
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Lazily loads the vendored SCIM static geometry (berries, caves, roads, …). */
function useScimStaticLayers(): ScimStaticLayers {
  const { data } = useQuery({
    queryKey: ['scim', 'static-layers'],
    queryFn: async (): Promise<ScimStaticLayers> => {
      const response = await fetch('/assets/scim/static-layers.json');
      if (!response.ok) throw new Error(`static-layers.json: HTTP ${response.status}`);
      return (await response.json()) as ScimStaticLayers;
    },
    staleTime: Infinity,
  });
  return data ?? {};
}

/** Lazily loads SCIM's building footprint outlines/colors by UE class name. */
function useBuildingModels(): BuildingModels {
  const { data } = useQuery({
    queryKey: ['scim', 'building-models'],
    queryFn: async (): Promise<BuildingModels> => {
      const response = await fetch('/assets/scim/building-models.json');
      if (!response.ok) throw new Error(`building-models.json: HTTP ${response.status}`);
      return (await response.json()) as BuildingModels;
    },
    staleTime: Infinity,
  });
  return data ?? {};
}

/** Belts render in SCIM's conveyor pink when the class has no vendored color. */
const BELT_FALLBACK_COLOR = '#FFC0CB';
/** SCIM's default power-line blue and pipeline orange. */
const CABLE_COLOR = '#0000ff';
const PIPE_COLOR = '#fa9549';
/** Building outlines only render from this zoom in; further out they are subpixel. */
const BUILDING_OUTLINE_MIN_ZOOM = 5;
/** SCIM's building hover highlight (light gray, near-opaque). */
const HOVER_STYLE = { fillColor: '#999999', fillOpacity: 0.9 };

/**
 * Layer visibility default: every live SCIM layer plus our live building
 * types ON, so the map is populated out of the box; vendored static layers
 * and the dense path layers (belts/cables/pipes) start OFF.
 */
const DEFAULT_ACTIVE_LAYERS: Record<string, boolean> = {
  ...Object.fromEntries(
    [...SCIM_LAYER_BY_ID.values()].filter((l) => !l.static).map((l) => [l.id, true]),
  ),
  'live:factory': true,
  'live:power_plant': true,
  'live:train_station': true,
  'live:drone_port': true,
  'live:truck_station': true,
  'live:artifact': true,
  'live:collectible': true,
  'live:wreck': true,
  'live:resource_node': true,
  'live:resource_well': true,
  'live:geyser': true,
};

/** Interactive world map: SCIM tiles/filters/visuals + live features, players, markers. */
export default function WorldMap() {
  const { data: world, isLoading } = useWorld();
  const markers = useMarkers();
  const staticLayers = useScimStaticLayers();
  const buildingModels = useBuildingModels();
  // Layer visibility persists in localStorage, keyed by SCIM layer id (plus
  // `live:<type>` for our live-only layers). Live layers start ON so the map
  // is populated out of the box; static/path layers start OFF.
  const [activeLayers, setActiveLayers] = useLocalStorage<Record<string, boolean>>(
    'spiffco.map.layers.v3',
    DEFAULT_ACTIVE_LAYERS,
  );
  const [baseLayer, setBaseLayer] = useLocalStorage<BaseLayerChoice>('spiffco.map.base', 'game');
  const [hideCollected, setHideCollected] = useLocalStorage('spiffco.map.hideCollected', false);
  const [nodeStatus, setNodeStatus] = useLocalStorage<'all' | 'free' | 'occupied'>(
    'spiffco.map.nodeStatus',
    'all',
  );
  const [produces, setProduces] = useLocalStorage('spiffco.map.produces', 'all');
  const [region, setRegion] = useLocalStorage('spiffco.map.region', 'all');
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [search, setSearch] = useState('');
  const [pending, setPending] = useState<{ lat: number; lng: number } | null>(null);
  const [pendingName, setPendingName] = useState('');
  // Initial view is read once (MapContainer ignores prop changes after mount);
  // ViewTracker keeps localStorage current and drives icon scaling.
  const [initialView] = useState(loadView);
  const [zoom, setZoom] = useState(initialView.zoom);
  const scale = iconScale(zoom);

  const allFeatures = useMemo(() => world?.features ?? [], [world]);
  const regionOptions = useMemo(() => metaOptions(allFeatures, 'region'), [allFeatures]);
  const producesOpts = useMemo(() => producesOptions(allFeatures), [allFeatures]);
  // Persisted dropdown values can outlive the data that offered them (e.g. a
  // region saved while in simulation mode — live FRM features carry no region).
  // A stale value would silently hide every live feature, so treat anything
  // absent from the current options as 'all'.
  const effectiveRegion = region !== 'all' && !regionOptions.includes(region) ? 'all' : region;
  const effectiveProduces =
    produces !== 'all' && !producesOpts.includes(produces) ? 'all' : produces;

  /** Live per-layer tallies (total/collected) for the panel badges. */
  const layerCounts = useMemo(() => {
    const counts: LayerCounts = {};
    for (const f of allFeatures) {
      const id = featureLayerId(f);
      const entry = (counts[id] ??= { total: 0, collected: 0 });
      entry.total += 1;
      if (f.collected === true) entry.collected += 1;
    }
    return counts;
  }, [allFeatures]);

  const belts = useMemo(() => world?.belts ?? [], [world]);
  const cables = useMemo(() => world?.cables ?? [], [world]);
  const pipes = useMemo(() => world?.pipes ?? [], [world]);

  /** Entries for live-only layers (`live:<type>`), shown in the Live section. */
  const liveEntries = useMemo(() => {
    const entries: LiveLayerEntry[] = [];
    for (const [id, count] of Object.entries(layerCounts)) {
      if (!id.startsWith('live:')) continue;
      const type = id.slice('live:'.length) as FeatureType;
      entries.push({
        id,
        label: FEATURE_LABEL[type] ?? type,
        color: FEATURE_COLOR[type] ?? '#94a3b8',
        count: count.total,
      });
    }
    entries.sort((a, b) => a.label.localeCompare(b.label));
    if (belts.length > 0) {
      entries.push({
        id: 'live:belts',
        label: 'Conveyor belts',
        color: BELT_FALLBACK_COLOR,
        count: belts.length,
      });
    }
    if (cables.length > 0) {
      entries.push({
        id: 'live:cables',
        label: 'Power lines',
        color: CABLE_COLOR,
        count: cables.length,
      });
    }
    if (pipes.length > 0) {
      entries.push({ id: 'live:pipes', label: 'Pipes', color: PIPE_COLOR, count: pipes.length });
    }
    return entries;
  }, [layerCounts, belts.length, cables.length, pipes.length]);

  const toggleLayer = (id: string) => setActiveLayers((v) => ({ ...v, [id]: !v[id] }));
  const setManyLayers = (ids: string[], on: boolean) =>
    setActiveLayers((v) => ({ ...v, ...Object.fromEntries(ids.map((id) => [id, on])) }));

  const allLayerIds = useMemo(
    () => [
      ...[...SCIM_LAYER_BY_ID.keys()],
      ...liveEntries.map((e) => e.id),
    ],
    [liveEntries],
  );

  const resetFilters = () => {
    setSearch('');
    setHideCollected(false);
    setNodeStatus('all');
    setProduces('all');
    setRegion('all');
    setActiveLayers(DEFAULT_ACTIVE_LAYERS);
  };

  const features = useMemo(
    () =>
      applyWorldFilters(allFeatures, {
        activeLayers,
        search,
        hideCollected,
        nodeStatus,
        produces: effectiveProduces,
        region: effectiveRegion,
      }),
    [allFeatures, activeLayers, search, hideCollected, nodeStatus, effectiveProduces, effectiveRegion],
  );

  const activeLayerCount = useMemo(
    () => Object.values(activeLayers).filter(Boolean).length,
    [activeLayers],
  );

  if (isLoading || !world) return <p className="text-sm text-slate-500">Loading world…</p>;

  return (
    <div className="flex h-full flex-col space-y-3">
      {/* Header: title, search, base-layer switcher, filters toggle. */}
      <div className="flex flex-wrap items-center gap-2 md:gap-3">
        <h1 className="text-xl font-semibold text-slate-100 md:text-2xl">World Map</h1>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search features…"
          className="min-w-0 flex-1 rounded-md border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none md:w-64 md:flex-none"
        />
        <span className="flex overflow-hidden rounded-md border border-surface-border text-xs">
          {BASE_LAYER_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setBaseLayer(option.value)}
              className={`px-2.5 py-1 transition-colors ${
                baseLayer === option.value
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-surface-raised text-slate-400 hover:text-slate-200'
              }`}
            >
              {option.label}
            </button>
          ))}
        </span>
        <span className="text-xs text-slate-500">
          {activeLayerCount > 0 ? `${activeLayerCount} layers on` : 'all layers off'}
        </span>
      </div>

      {/* The map gets the room: fills the viewport height, filters sit below. */}
      <Card className="relative min-h-[26rem] flex-1 basis-[70vh] shrink-0 !p-1">
        <MapContainer
          crs={CRS.Simple}
          center={initialView.center}
          zoom={initialView.zoom}
          minZoom={MIN_TILE_ZOOM}
          maxZoom={MAX_ZOOM}
          // Fractional zoom steps + soft pan bounds, matching SCIM's map feel.
          zoomSnap={0.25}
          zoomDelta={0.25}
          wheelPxPerZoomLevel={90}
          maxBounds={MAP_BOUNDS}
          maxBoundsViscosity={0.6}
          preferCanvas
          className="h-full min-h-[26rem] w-full rounded-md bg-[#10131a]"
          attributionControl={false}
        >
          {(baseLayer === 'game' || baseLayer === 'realistic') && (
            <TileLayer
              key={baseLayer}
              url={scimTileUrl(baseLayer === 'game' ? 'gameLayer' : 'realisticLayer')}
              bounds={MAP_BOUNDS}
              minNativeZoom={MIN_TILE_ZOOM}
              maxNativeZoom={MAX_NATIVE_ZOOM}
              noWrap
              // The CDN hotlink-protects by Referer; without this the browser
              // sends one and every tile request 403s.
              referrerPolicy="no-referrer"
            />
          )}
          {baseLayer === 'offline' && (
            <ImageOverlay url={MAP_IMAGE_URL} bounds={MAP_IMAGE_BOUNDS} opacity={0.9} />
          )}
          <AddMarkerOnClick
            onPick={(e) => {
              setPending({ lat: e.latlng.lat, lng: e.latlng.lng });
              setPendingName('');
            }}
          />
          <CursorTracker onMove={setCursor} />
          <ViewTracker onZoom={setZoom} />

          {/* Live world features (FRM / simulation), filtered by layer.
              Buildings whose class has a SCIM footprint render as their real
              rotated outline once zoomed in; everything else uses pins. */}
          {features.map((f) => {
            const stateSuffix =
              f.collected === true
                ? ' (collected)'
                : f.occupied === true
                  ? ' (miner installed)'
                  : f.occupied === false
                    ? ' (free)'
                    : '';
            const isBuilding = f.type === 'factory' || f.type === 'power_plant';
            const model = isBuilding
              ? buildingModels[String(f.meta.class_name ?? '')]
              : undefined;
            // Buildings get SCIM's game-styled panel; everything else keeps
            // the plain details popup.
            const details = isBuilding ? (
              <Popup className="scim-popup" maxWidth={280}>
                <BuildingPanel feature={f} model={model} />
              </Popup>
            ) : (
              <Popup>
                <strong>{f.name}</strong>
                <br />
                {FEATURE_LABEL[f.type].replace(/s$/, '') + stateSuffix}
                {Object.entries(f.meta).map(([k, v]) => (
                  <div key={k}>
                    {k}: {String(v)}
                  </div>
                ))}
              </Popup>
            );
            if (isBuilding && zoom >= BUILDING_OUTLINE_MIN_ZOOM) {
              const fillColor = model?.color ?? FEATURE_COLOR[f.type];
              const fillOpacity = model?.opacity ?? 0.5;
              const outline = buildingOutline(
                model,
                f.position,
                Number(f.meta.rotation ?? 0),
              );
              if (outline) {
                return outline.map((rings, i) => (
                  <Polygon
                    key={`${f.id}-${i}`}
                    positions={rings}
                    pathOptions={{
                      color: fillColor,
                      fillColor,
                      weight: model?.weight ?? 2,
                      opacity: 0.9,
                      fillOpacity,
                    }}
                    // SCIM's hover animation: light-gray highlight on
                    // mouseover, restored on mouseout.
                    eventHandlers={{
                      mouseover: (e) => (e.target as Path).setStyle(HOVER_STYLE),
                      mouseout: (e) => (e.target as Path).setStyle({ fillColor, fillOpacity }),
                    }}
                  >
                    <Tooltip sticky>{f.name}</Tooltip>
                    {i === 0 ? details : null}
                  </Polygon>
                ));
              }
            }
            return (
              <Marker key={f.id} position={toLatLng(f.position)} icon={featureIcon(f, scale)}>
                <Tooltip direction="top" offset={[0, -40 * scale]}>
                  {f.name + stateSuffix}
                </Tooltip>
                {details}
              </Marker>
            );
          })}

          {/* Power lines (blue, as on SCIM) and pipelines. */}
          {activeLayers['live:cables'] &&
            cables.map((cable) => (
              <Polyline
                key={cable.id}
                positions={cable.points.map((p) => toLatLng(p))}
                pathOptions={{ color: CABLE_COLOR, weight: 2, opacity: 0.9 }}
              >
                <Tooltip sticky>{cable.name}</Tooltip>
              </Polyline>
            ))}
          {activeLayers['live:pipes'] &&
            pipes.map((pipe) => (
              <Polyline
                key={pipe.id}
                positions={pipe.points.map((p) => toLatLng(p))}
                pathOptions={{ color: PIPE_COLOR, weight: 3, opacity: 0.85 }}
              >
                <Tooltip sticky>{pipe.name}</Tooltip>
              </Polyline>
            ))}

          {/* Conveyor belts (FRM getBelts splines), colored per belt mark. */}
          {activeLayers['live:belts'] &&
            belts.map((belt) => (
              <Polyline
                key={belt.id}
                positions={belt.points.map((p) => toLatLng(p))}
                pathOptions={{
                  color: buildingModels[belt.class_name]?.color ?? BELT_FALLBACK_COLOR,
                  weight: 3,
                  opacity: 0.85,
                }}
              >
                <Tooltip sticky>
                  {belt.name}
                  {belt.items_per_minute != null ? ` · ${belt.items_per_minute}/min` : ''}
                </Tooltip>
              </Polyline>
            ))}

          {/* Vendored SCIM static layers (no FRM endpoint exists for these). */}
          {STATIC_PIN_LAYERS.map((layerId) => {
            const layer = SCIM_LAYER_BY_ID.get(layerId);
            const points = staticLayers[layerId];
            if (!activeLayers[layerId] || !layer || !points) return null;
            const icon = scimLayerIcon(layer, Math.min(scale, 0.85));
            return points.map(([x, y, z], i) => (
              <Marker key={`${layerId}-${i}`} position={toLatLng({ x, y, z })} icon={icon}>
                <Popup>{layer.name}</Popup>
              </Marker>
            ));
          })}
          {Object.entries(STATIC_CIRCLE_STYLE).map(([layerId, style]) => {
            const points = staticLayers[layerId as 'sporeFlowers'];
            if (!activeLayers[layerId] || !points) return null;
            const name = SCIM_LAYER_BY_ID.get(layerId)?.name ?? layerId;
            return points.map(([x, y, z], i) => (
              <Circle
                key={`${layerId}-${i}`}
                center={toLatLng({ x, y, z })}
                radius={style.radius}
                pathOptions={{ color: style.color, weight: 1, fillOpacity: 0.4 }}
              >
                <Popup>{name}</Popup>
              </Circle>
            ));
          })}
          {activeLayers.spawn &&
            (staticLayers.spawn ?? []).map((s, i) => (
              <Circle
                key={`spawn-${i}`}
                center={toLatLng({ x: s.x, y: s.y, z: 0 })}
                radius={s.radius / 6000}
                pathOptions={{ color: '#3388ff', weight: 2, fillOpacity: 0.1 }}
              >
                <Tooltip>Spawn area</Tooltip>
              </Circle>
            ))}
          {activeLayers.worldBorder && staticLayers.worldBorder && (
            <Polyline
              positions={staticLayers.worldBorder.map(([x, y]) => toLatLng({ x, y, z: 0 }))}
              pathOptions={{ color: 'red', weight: 3, interactive: false }}
            />
          )}
          {activeLayers.caves &&
            Object.entries(staticLayers.caves ?? {}).map(([caveId, cave]) => (
              <Fragment key={`cave-${caveId}`}>
                <Polygon
                  positions={[
                    cave.points.map(([x, y]) => toLatLng({ x, y, z: 0 })),
                    ...(cave.holes ?? []).map((hole) =>
                      hole.map(([x, y]) => toLatLng({ x, y, z: 0 })),
                    ),
                  ]}
                  pathOptions={{ color: 'yellow', weight: 1, interactive: false }}
                />
                {(cave.entrances ?? []).map((entrance, i) => (
                  <Polyline
                    key={i}
                    positions={entrance.map((point) =>
                      toLatLng({ x: point[0], y: point[1], z: 0 }),
                    )}
                    pathOptions={{ color: 'yellow', weight: 3, dashArray: '10 10' }}
                  />
                ))}
              </Fragment>
            ))}
          {activeLayers.roads &&
            Object.entries(staticLayers.roads ?? {}).map(([roadId, road]) => (
              <Polyline
                key={`road-${roadId}`}
                positions={road.points.map(([x, y]) => toLatLng({ x, y, z: 0 }))}
                pathOptions={{ color: 'purple', weight: 5, opacity: 0.7 }}
              >
                {road.name && <Tooltip sticky>{road.name}</Tooltip>}
              </Polyline>
            ))}

          {world.players.map((p) => (
            <CircleMarker
              key={p.id}
              center={toLatLng(p.position)}
              radius={8}
              pathOptions={{ color: '#fff', weight: 2, fillColor: PLAYER_COLOR, fillOpacity: 1 }}
            >
              <Tooltip direction="top" offset={[0, -8]} permanent>
                {p.name}
              </Tooltip>
            </CircleMarker>
          ))}

          {(markers.data ?? []).map((m) => (
            <CircleMarker
              key={m.id}
              center={toLatLng(m.position)}
              radius={6}
              pathOptions={{
                color: m.color || MARKER_COLOR,
                weight: 2,
                fillColor: 'transparent',
                fillOpacity: 0,
              }}
            >
              <Popup>
                <strong>{m.name}</strong>
                {m.notes && <p>{m.notes}</p>}
                <button
                  onClick={() => markers.remove.mutate(m.id)}
                  className="mt-1 text-xs text-red-400 underline"
                >
                  Delete marker
                </button>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-md border border-surface-border bg-surface/85 px-2.5 py-1 font-mono text-xs text-slate-300 backdrop-blur">
          {cursor
            ? `X ${Math.round(cursor.x).toLocaleString()}  ·  Y ${Math.round(cursor.y).toLocaleString()}`
            : 'move cursor for coordinates'}
        </div>
      </Card>

      {pending && (
        <Card title="New marker">
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!pendingName.trim()) return;
              markers.create.mutate({
                name: pendingName.trim(),
                position: fromLatLng(pending.lat, pending.lng),
              });
              setPending(null);
            }}
          >
            <input
              autoFocus
              value={pendingName}
              onChange={(e) => setPendingName(e.target.value)}
              placeholder="Marker name"
              className="w-64 rounded-md border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-slate-200 focus:border-accent focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-surface hover:bg-accent-hover"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => setPending(null)}
              className="rounded-md px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
          </form>
        </Card>
      )}

      {/* Filter section below the map; each category collapses via its arrow. */}
      <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <SelectFilter
              icon="🔧"
              label="Node status"
              value={nodeStatus}
              onChange={(v) => setNodeStatus(v as 'all' | 'free' | 'occupied')}
              options={[
                { value: 'all', label: 'All' },
                { value: 'free', label: 'Free' },
                { value: 'occupied', label: 'Miner installed' },
              ]}
            />
            <SelectFilter
              icon="🗺️"
              label="Region"
              value={effectiveRegion}
              onChange={setRegion}
              options={[
                { value: 'all', label: 'All' },
                ...regionOptions.map((r) => ({ value: r, label: r })),
              ]}
            />
            {producesOpts.length > 0 && (
              <SelectFilter
                icon="🏭"
                label="Produces"
                value={effectiveProduces}
                onChange={setProduces}
                options={[
                  { value: 'all', label: 'All' },
                  ...producesOpts.map((p) => ({ value: p, label: p })),
                ]}
              />
            )}
            <button
              onClick={() => setHideCollected((v) => !v)}
              className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                hideCollected
                  ? 'border-accent/50 bg-accent/10 text-accent'
                  : 'border-surface-border bg-surface-raised text-slate-400'
              }`}
            >
              Hide collected
            </button>
            <button
              onClick={() => setManyLayers(allLayerIds, true)}
              className="rounded-md border border-emerald-600/50 bg-emerald-600/10 px-2.5 py-1 text-xs text-emerald-400 hover:bg-emerald-600/20"
            >
              ✓ Enable all
            </button>
            <button
              onClick={() => setManyLayers(allLayerIds, false)}
              className="rounded-md border border-surface-border bg-surface-raised px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
            >
              ✕ Disable all
            </button>
            <button
              onClick={resetFilters}
              className="flex items-center gap-1.5 rounded-md border border-surface-border bg-surface-raised px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
            >
              ↺ Reset filters
            </button>
          </div>

          <MapLayerPanel
            categories={SCIM_CATEGORIES}
            liveEntries={liveEntries}
            active={activeLayers}
            counts={layerCounts}
            onToggle={toggleLayer}
            onSetMany={setManyLayers}
          />

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            <span className="flex items-center gap-2">
              <span className="text-slate-400">Node purity:</span>
              {(['impure', 'normal', 'pure'] as const).map((p) => (
                <span key={p} className="flex items-center gap-1">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ background: PURITY_COLOR[p] }}
                  />
                  {p}
                </span>
              ))}
            </span>
            <span>
              · Right-click to add a marker · dimmed = collected / miner installed · a specific
              region shows only located features
            </span>
          </div>
      </div>
    </div>
  );
}
