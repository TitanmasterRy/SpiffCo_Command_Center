import { useLocalStorage } from '../hooks/useLocalStorage';
import type { ScimCategory, ScimLayer } from '../types/scim';

/** A live-only layer entry (features without a SCIM layer: factories, …). */
export interface LiveLayerEntry {
  id: string;
  label: string;
  color: string;
  count: number;
}

/** Live per-layer tallies (total / collected) keyed by layer id. */
export type LayerCounts = Record<string, { total: number; collected: number }>;

interface MapLayerPanelProps {
  categories: ScimCategory[];
  /** Extra "Live" category entries appended after the SCIM categories. */
  liveEntries: LiveLayerEntry[];
  active: Record<string, boolean>;
  /** Live feature tallies; layers absent here fall back to vendored counts. */
  counts: LayerCounts;
  onToggle: (layerId: string) => void;
  onSetMany: (layerIds: string[], on: boolean) => void;
}

const numberFormat = new Intl.NumberFormat();

function LayerButton({
  layer,
  active,
  count,
  onToggle,
}: {
  layer: ScimLayer;
  active: boolean;
  count: { total: number; collected: number } | undefined;
  onToggle: () => void;
}) {
  const total = count?.total ?? layer.count;
  const collected = count?.collected ?? 0;
  const badge =
    collected > 0
      ? `${numberFormat.format(collected)}/${numberFormat.format(total)}`
      : numberFormat.format(total);
  return (
    <button
      onClick={onToggle}
      title={layer.name}
      className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors ${
        active
          ? 'border-amber-500/70 bg-amber-500/10 text-slate-100'
          : 'border-surface-border bg-surface-raised text-slate-500 hover:text-slate-300'
      }`}
    >
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
        style={{
          background: layer.insideColor ?? '#666',
          border: `2px solid ${layer.outsideColor ?? '#666'}`,
          opacity: active ? 1 : 0.45,
        }}
      >
        {layer.icon && (
          <img
            src={layer.icon}
            alt=""
            style={{ width: 14, height: 14, minWidth: 0, objectFit: 'contain', display: 'block' }}
          />
        )}
      </span>
      <span className="truncate">{layer.name}</span>
      {total > 0 && <span className="tabular-nums text-slate-500">{badge}</span>}
    </button>
  );
}

interface CategoryHeaderProps {
  name: string;
  collapsed: boolean;
  activeCount: number;
  onCollapse: () => void;
  onAll: () => void;
  onNone: () => void;
}

/** Category header row: collapse arrow, name, active count, all/none. */
function CategoryHeader({
  name,
  collapsed,
  activeCount,
  onCollapse,
  onAll,
  onNone,
}: CategoryHeaderProps) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onCollapse}
        aria-expanded={!collapsed}
        className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300 hover:text-slate-100"
      >
        <span
          className={`inline-block text-[10px] transition-transform ${collapsed ? '' : 'rotate-90'}`}
          aria-hidden
        >
          ▶
        </span>
        {name}
        {activeCount > 0 && (
          <span className="rounded-full bg-amber-500/20 px-1.5 text-[10px] font-normal normal-case text-amber-300">
            {activeCount} on
          </span>
        )}
      </button>
      {!collapsed && (
        <>
          <button onClick={onAll} className="text-[11px] text-emerald-400 hover:text-emerald-300">
            all
          </button>
          <button onClick={onNone} className="text-[11px] text-slate-500 hover:text-slate-300">
            none
          </button>
        </>
      )}
    </div>
  );
}

/**
 * SCIM-style categorized layer panel: every category (Resource nodes, Power
 * Slugs, Artifacts, Collectibles, World, Live) lists its layers as toggle
 * buttons with count badges (collected/total for live pickups). Each category
 * collapses via the arrow next to its name; the collapsed set persists.
 */
export function MapLayerPanel({
  categories,
  liveEntries,
  active,
  counts,
  onToggle,
  onSetMany,
}: MapLayerPanelProps) {
  const [collapsed, setCollapsed] = useLocalStorage<Record<string, boolean>>(
    'spiffco.map.panelCollapsed',
    {},
  );
  const toggleCollapsed = (id: string) => setCollapsed((c) => ({ ...c, [id]: !c[id] }));
  const categoryIds = (category: ScimCategory) =>
    category.groups.flatMap((group) => group.layers.map((layer) => layer.id));
  const activeCount = (ids: string[]) => ids.filter((id) => active[id]).length;

  return (
    <div className="space-y-2">
      {categories.map((category) => {
        const ids = categoryIds(category);
        return (
          <div key={category.id} className="space-y-1.5">
            <CategoryHeader
              name={category.name}
              collapsed={!!collapsed[category.id]}
              activeCount={activeCount(ids)}
              onCollapse={() => toggleCollapsed(category.id)}
              onAll={() => onSetMany(ids, true)}
              onNone={() => onSetMany(ids, false)}
            />
            {!collapsed[category.id] &&
              category.groups.map((group) => (
                <div key={group.name} className="flex flex-wrap items-center gap-1.5">
                  {category.groups.length > 1 && group.layers.length > 1 && (
                    <span
                      className="w-24 shrink-0 truncate text-[11px] text-slate-500"
                      title={group.name}
                    >
                      {group.name}
                    </span>
                  )}
                  {group.layers.map((layer) => (
                    <LayerButton
                      key={layer.id}
                      layer={layer}
                      active={!!active[layer.id]}
                      count={counts[layer.id]}
                      onToggle={() => onToggle(layer.id)}
                    />
                  ))}
                </div>
              ))}
          </div>
        );
      })}

      {liveEntries.length > 0 && (
        <div className="space-y-1.5">
          <CategoryHeader
            name="Live"
            collapsed={!!collapsed.live}
            activeCount={activeCount(liveEntries.map((e) => e.id))}
            onCollapse={() => toggleCollapsed('live')}
            onAll={() => onSetMany(liveEntries.map((e) => e.id), true)}
            onNone={() => onSetMany(liveEntries.map((e) => e.id), false)}
          />
          {!collapsed.live && (
            <div className="flex flex-wrap items-center gap-1.5">
              {liveEntries.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => onToggle(entry.id)}
                  className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors ${
                    active[entry.id]
                      ? 'border-amber-500/70 bg-amber-500/10 text-slate-100'
                      : 'border-surface-border bg-surface-raised text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: entry.color, opacity: active[entry.id] ? 1 : 0.4 }}
                  />
                  {entry.label}
                  <span className="tabular-nums text-slate-500">
                    {numberFormat.format(entry.count)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
