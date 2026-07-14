import { CRS, type LeafletMouseEvent } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMemo, useState } from 'react';
import {
  CircleMarker,
  ImageOverlay,
  MapContainer,
  Marker,
  Popup,
  Rectangle,
  Tooltip,
  useMapEvents,
} from 'react-leaflet';
import { Card } from '../components/Card';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useWorld, useMarkers } from '../hooks/useWorld';
import type { FeatureType } from '../types/world';
import { fromLatLng, MAP_IMAGE_BOUNDS, MAP_IMAGE_URL, toLatLng } from '../utils/mapCoords';
import { FEATURE_COLOR, featureIcon, pickupKindIconHtml, PURITY_COLOR } from '../utils/mapIcons';
import {
  applyWorldFilters,
  metaOptions,
  NODE_LIKE_TYPES,
  pickupKindOptions,
  producesOptions,
} from '../utils/worldFilters';

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
const PICKUP_TYPES: ReadonlySet<FeatureType> = new Set(['artifact', 'collectible', 'wreck']);
const PLAYER_COLOR = '#e66767';
const MARKER_COLOR = '#94a3b8';

/** A layer-visibility map with every feature type set to ``on``. */
const allLayers = (on: boolean): Record<FeatureType, boolean> =>
  Object.fromEntries((Object.keys(FEATURE_LABEL) as FeatureType[]).map((t) => [t, on])) as Record<
    FeatureType,
    boolean
  >;

/** Playable world extent in km (game is ~750×750 km at our 1 unit = 1 km scale). */
const WORLD_BOUNDS: [[number, number], [number, number]] = [
  [-400, -400],
  [400, 400],
];

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

/** Interactive world map: features, live players, layers, search, custom markers. */
export default function WorldMap() {
  const { data: world, isLoading } = useWorld();
  const markers = useMarkers();
  // Filter state persists in localStorage. All layers start OFF by default so
  // the map opens empty and the user enables just the layers they care about.
  const [visible, setVisible] = useLocalStorage('spiffco.map.layers', allLayers(false));
  const [hideCollected, setHideCollected] = useLocalStorage('spiffco.map.hideCollected', false);
  const [showMap, setShowMap] = useLocalStorage('spiffco.map.background', true);
  const [resource, setResource] = useLocalStorage('spiffco.map.resource', 'all');
  const [purity, setPurity] = useLocalStorage('spiffco.map.purity', 'all');
  const [nodeStatus, setNodeStatus] = useLocalStorage<'all' | 'free' | 'occupied'>(
    'spiffco.map.nodeStatus',
    'all',
  );
  const [pickupKinds, setPickupKinds] = useLocalStorage<Record<string, boolean>>(
    'spiffco.map.pickupKinds',
    {},
  );
  const [produces, setProduces] = useLocalStorage('spiffco.map.produces', 'all');
  const [region, setRegion] = useLocalStorage('spiffco.map.region', 'all');
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [search, setSearch] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false); // mobile: collapse the filter panel
  const [pending, setPending] = useState<{ lat: number; lng: number } | null>(null);
  const [pendingName, setPendingName] = useState('');

  const allFeatures = useMemo(() => world?.features ?? [], [world]);
  const nodeFeatures = useMemo(
    () => allFeatures.filter((f) => NODE_LIKE_TYPES.has(f.type)),
    [allFeatures],
  );
  const resourceOptions = useMemo(() => metaOptions(nodeFeatures, 'resource'), [nodeFeatures]);
  const regionOptions = useMemo(() => metaOptions(allFeatures, 'region'), [allFeatures]);
  const kindOptions = useMemo(() => pickupKindOptions(allFeatures), [allFeatures]);
  const kindCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const f of allFeatures) {
      if (PICKUP_TYPES.has(f.type)) {
        const k = String(f.meta.kind ?? '');
        if (k) c[k] = (c[k] ?? 0) + 1;
      }
    }
    return c;
  }, [allFeatures]);
  const producesOpts = useMemo(() => producesOptions(allFeatures), [allFeatures]);

  const toggleKind = (k: string) => setPickupKinds((v) => ({ ...v, [k]: !v[k] }));

  /** Turn every layer and pickup kind on or off at once. */
  const setAll = (on: boolean) => {
    setVisible(allLayers(on));
    setPickupKinds(Object.fromEntries(kindOptions.map((k) => [k, on])));
  };

  const resetFilters = () => {
    setSearch('');
    setHideCollected(false);
    setResource('all');
    setPurity('all');
    setNodeStatus('all');
    setProduces('all');
    setRegion('all');
    setAll(false); // back to the all-off default
  };

  const features = useMemo(
    () =>
      applyWorldFilters(allFeatures, {
        visible,
        pickupKinds,
        search,
        hideCollected,
        resource,
        purity,
        nodeStatus,
        produces,
        region,
      }),
    [allFeatures, visible, pickupKinds, search, hideCollected, resource, purity, nodeStatus, produces, region],
  );

  if (isLoading || !world) return <p className="text-sm text-slate-500">Loading world…</p>;

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 md:gap-3">
          <h1 className="text-xl font-semibold text-slate-100 md:text-2xl">World Map</h1>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search features…"
            className="min-w-0 flex-1 rounded-md border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none md:w-64 md:flex-none"
          />
          <button
            onClick={() => setFiltersOpen((o) => !o)}
            className="rounded-md border border-surface-border bg-surface-raised px-3 py-1.5 text-sm text-slate-300 md:hidden"
            aria-expanded={filtersOpen}
          >
            Filters {filtersOpen ? '▲' : '▼'}
          </button>
        </div>

        {/* Filter panel — collapsible on mobile, always shown at md+. */}
        <div className={`${filtersOpen ? 'block' : 'hidden'} space-y-3 md:block`}>
        {/* Dropdown filters — kept at the top, each with an icon. */}
        <div className="flex flex-wrap items-center gap-2">
          <SelectFilter
            icon="⛏️"
            label="Resource"
            value={resource}
            onChange={setResource}
            options={[
              { value: 'all', label: 'All' },
              ...resourceOptions.map((r) => ({ value: r, label: r })),
            ]}
          />
          <SelectFilter
            icon="💎"
            label="Purity"
            value={purity}
            onChange={setPurity}
            options={[
              { value: 'all', label: 'All' },
              { value: 'impure', label: 'Impure' },
              { value: 'normal', label: 'Normal' },
              { value: 'pure', label: 'Pure' },
            ]}
          />
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
            value={region}
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
              value={produces}
              onChange={setProduces}
              options={[
                { value: 'all', label: 'All' },
                ...producesOpts.map((p) => ({ value: p, label: p })),
              ]}
            />
          )}
          <button
            onClick={resetFilters}
            className="flex items-center gap-1.5 rounded-md border border-surface-border bg-surface-raised px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
          >
            ↺ Reset filters
          </button>
        </div>

        {/* Layer toggles (non-pickup types) + bulk enable/disable. */}
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            onClick={() => setAll(true)}
            className="rounded-full border border-emerald-600/50 bg-emerald-600/10 px-2.5 py-1 text-emerald-400 hover:bg-emerald-600/20"
          >
            ✓ Enable all
          </button>
          <button
            onClick={() => setAll(false)}
            className="rounded-full border border-surface-border bg-surface-raised px-2.5 py-1 text-slate-400 hover:text-slate-200"
          >
            ✕ Disable all
          </button>
          <span className="mx-1 w-px self-stretch bg-surface-border" />
          {(Object.keys(FEATURE_LABEL) as FeatureType[])
            .filter((type) => !PICKUP_TYPES.has(type))
            .map((type) => (
              <button
                key={type}
                onClick={() => setVisible((v) => ({ ...v, [type]: !v[type] }))}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors ${
                  visible[type]
                    ? 'border-surface-border bg-surface-raised text-slate-200'
                    : 'border-transparent bg-surface-overlay text-slate-500'
                }`}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: FEATURE_COLOR[type], opacity: visible[type] ? 1 : 0.3 }}
                />
                {FEATURE_LABEL[type]}
              </button>
            ))}
          <button
            onClick={() => setShowMap((v) => !v)}
            className={`rounded-full border px-2.5 py-1 transition-colors ${
              showMap
                ? 'border-accent/50 bg-accent/10 text-accent'
                : 'border-surface-border bg-surface-raised text-slate-400'
            }`}
          >
            Map background
          </button>
        </div>

        {/* Per-pickup toggles (each pickup kind has its own filter). */}
        {kindOptions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">Pickups:</span>
            {kindOptions.map((k) => (
              <button
                key={k}
                onClick={() => toggleKind(k)}
                className={`flex items-center gap-1.5 rounded-full border px-2 py-1 transition-colors ${
                  pickupKinds[k]
                    ? 'border-surface-border bg-surface-raised text-slate-200'
                    : 'border-transparent bg-surface-overlay text-slate-500'
                }`}
              >
                <span
                  className="inline-flex h-4 w-4 items-center justify-center"
                  style={{ opacity: pickupKinds[k] ? 1 : 0.4 }}
                  dangerouslySetInnerHTML={{ __html: pickupKindIconHtml(k) }}
                />
                {k.replace(/-/g, ' ')}
                <span className="tabular-nums text-slate-500">{kindCounts[k]}</span>
              </button>
            ))}
            <button
              onClick={() => setHideCollected((v) => !v)}
              className={`rounded-full border px-2.5 py-1 transition-colors ${
                hideCollected
                  ? 'border-accent/50 bg-accent/10 text-accent'
                  : 'border-surface-border bg-surface-raised text-slate-400'
              }`}
            >
              Hide collected
            </button>
          </div>
        )}

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

      <Card className="relative min-h-[24rem] flex-1 !p-1">
        <MapContainer
          crs={CRS.Simple}
          center={[-120, -50]}
          zoom={1}
          minZoom={-1}
          maxZoom={6}
          className="h-[70vh] w-full rounded-md bg-[#10131a] md:h-[32rem]"
          attributionControl={false}
        >
          {showMap && (
            <ImageOverlay url={MAP_IMAGE_URL} bounds={MAP_IMAGE_BOUNDS} opacity={0.85} />
          )}
          <Rectangle
            bounds={WORLD_BOUNDS}
            pathOptions={{ color: '#323945', weight: 1, fill: false, dashArray: '4 6' }}
          />
          <AddMarkerOnClick
            onPick={(e) => {
              setPending({ lat: e.latlng.lat, lng: e.latlng.lng });
              setPendingName('');
            }}
          />
          <CursorTracker onMove={setCursor} />

          {features.map((f) => {
            const stateSuffix =
              f.collected === true
                ? ' (collected)'
                : f.occupied === true
                  ? ' (miner installed)'
                  : f.occupied === false
                    ? ' (free)'
                    : '';
            return (
              <Marker key={f.id} position={toLatLng(f.position)} icon={featureIcon(f)}>
                <Tooltip direction="top" offset={[0, -14]}>
                  {f.name + stateSuffix}
                </Tooltip>
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
              </Marker>
            );
          })}

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
    </div>
  );
}
