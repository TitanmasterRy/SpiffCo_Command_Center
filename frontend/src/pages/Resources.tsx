import { Card } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import { useWorld } from '../hooks/useWorld';
import type { MapFeature } from '../types/world';

/** Display order + colors for node purity (best first). */
const PURITIES = ['pure', 'normal', 'impure'] as const;
type Purity = (typeof PURITIES)[number];

const PURITY_STYLE: Record<Purity, string> = {
  pure: 'text-status-ok',
  normal: 'text-slate-200',
  impure: 'text-status-warn',
};

/** "iron-ore" → "Iron Ore". */
function titleize(id: string): string {
  return id
    .split(/[-_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

interface ResourceGroup {
  resource: string;
  nodes: MapFeature[];
  occupied: number;
  byPurity: Record<string, number>;
}

function groupByResource(nodes: MapFeature[]): ResourceGroup[] {
  const groups = new Map<string, ResourceGroup>();
  for (const node of nodes) {
    const resource = String(node.meta.resource ?? 'unknown');
    let group = groups.get(resource);
    if (!group) {
      group = { resource, nodes: [], occupied: 0, byPurity: {} };
      groups.set(resource, group);
    }
    group.nodes.push(node);
    if (node.occupied) group.occupied += 1;
    const purity = String(node.meta.purity ?? 'normal');
    group.byPurity[purity] = (group.byPurity[purity] ?? 0) + 1;
  }
  return [...groups.values()].sort((a, b) => b.nodes.length - a.nodes.length);
}

/** Order purity keys as pure→normal→impure, with any unknown keys last. */
function orderedPurities(byPurity: Record<string, number>): [string, number][] {
  const known = PURITIES.filter((p) => byPurity[p] !== undefined).map(
    (p) => [p, byPurity[p]] as [string, number],
  );
  const extra = Object.entries(byPurity).filter(
    ([p]) => !PURITIES.includes(p as Purity),
  );
  return [...known, ...extra];
}

function ResourceCard({ group }: { group: ResourceGroup }) {
  const total = group.nodes.length;
  const regions = [...new Set(group.nodes.map((n) => String(n.meta.region ?? '—')))];
  return (
    <Card title={titleize(group.resource)}>
      <div className="space-y-3">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums text-slate-100">{total}</span>
          <span className="text-sm text-slate-500">
            node{total === 1 ? '' : 's'} · {group.occupied} mined
          </span>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {orderedPurities(group.byPurity).map(([purity, count]) => (
            <span key={purity} className={PURITY_STYLE[purity as Purity] ?? 'text-slate-300'}>
              <span className="font-semibold tabular-nums">{count}</span>{' '}
              <span className="text-xs uppercase tracking-wider">{purity}</span>
            </span>
          ))}
        </div>
        <p className="text-xs text-slate-500">{regions.join(' · ')}</p>
      </div>
    </Card>
  );
}

/** Resource-node overview: purity, region, and extractor occupancy by resource. */
export default function Resources() {
  const { data: snap, isLoading } = useWorld();

  if (isLoading || !snap) {
    return <p className="text-sm text-slate-500">Loading resources…</p>;
  }

  const nodes = snap.features.filter((f) => f.type === 'resource_node');
  const groups = groupByResource(nodes);
  const occupied = nodes.filter((n) => n.occupied).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Resources</h1>
        {snap.source === 'simulation' && (
          <StatusBadge kind="idle" label="Simulated data — connect FRM in Settings" />
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Resource nodes" value={`${nodes.length}`} detail={`${groups.length} resource types`} />
        <StatCard
          title="Mined"
          value={`${occupied}`}
          detail={`${nodes.length - occupied} unexploited`}
        />
        <StatCard
          title="Utilization"
          value={`${Math.round((occupied / (nodes.length || 1)) * 100)}%`}
          detail="nodes with an extractor"
        />
        <StatCard
          title="Available"
          value={`${nodes.length - occupied}`}
          detail={nodes.length - occupied === 0 ? 'all nodes tapped' : 'open for extraction'}
        />
      </div>

      {nodes.length === 0 ? (
        <Card title="Resource nodes">
          <p className="text-sm text-slate-500">No resource nodes reported yet.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {groups.map((g) => (
            <ResourceCard key={g.resource} group={g} />
          ))}
        </div>
      )}
    </div>
  );
}
