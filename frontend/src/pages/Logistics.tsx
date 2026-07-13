import { useMemo } from 'react';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { useLogistics } from '../hooks/useLogistics';
import type { LogisticsMode } from '../types/logistics';
import { formatPerMinute } from '../utils/format';
import { makeProjector, routeWidth, utilizationColor } from '../utils/logisticsView';

const VIEW = { width: 760, height: 440, padding: 28 };

const NODE_COLOR: Record<string, string> = {
  factory: '#3987e5',
  station: '#9085e9',
  port: '#199e70',
};

const MODE_LABEL: Record<LogisticsMode, string> = {
  belt: 'Belt',
  pipe: 'Pipe',
  train: 'Train',
  truck: 'Truck',
  drone: 'Drone',
};

/** Logistics network (Phase 6): schematic, throughput table, and live trains. */
export default function Logistics() {
  const { data: snap, isLoading } = useLogistics();

  const project = useMemo(() => (snap ? makeProjector(snap.nodes, VIEW) : null), [snap]);
  const nodePos = useMemo(() => {
    if (!snap || !project) return {};
    return Object.fromEntries(snap.nodes.map((n) => [n.id, project(n.position)]));
  }, [snap, project]);

  if (isLoading || !snap || !project) {
    return <p className="text-sm text-slate-500">Loading logistics…</p>;
  }

  const { summary } = snap;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Logistics</h1>
        <div className="flex items-center gap-2">
          {snap.source === 'simulation' && (
            <StatusBadge kind="idle" label="Simulated — FRM arrives in Phase 11" />
          )}
          {summary.over_capacity_routes.length > 0 && (
            <StatusBadge
              kind="error"
              label={`${summary.over_capacity_routes.length} over capacity`}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_18rem]">
        <Card title="Network">
          <div className="overflow-auto">
            <svg
              width={VIEW.width}
              height={VIEW.height}
              role="img"
              aria-label="Logistics network schematic"
            >
              {snap.routes.map((r) => {
                const a = nodePos[r.from_node];
                const b = nodePos[r.to_node];
                if (!a || !b) return null;
                return (
                  <g key={r.id}>
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={utilizationColor(r.utilization)}
                      strokeWidth={routeWidth(r.throughput_per_min)}
                      strokeOpacity={0.8}
                      strokeDasharray={r.mode === 'drone' ? '4 4' : undefined}
                    >
                      <title>
                        {r.name} · {MODE_LABEL[r.mode]} · {formatPerMinute(r.throughput_per_min)} /{' '}
                        {formatPerMinute(r.capacity_per_min)} ({Math.round(r.utilization * 100)}%)
                      </title>
                    </line>
                  </g>
                );
              })}
              {snap.trains.map((t) => {
                const p = project(t.position);
                return (
                  <rect key={t.id} x={p.x - 4} y={p.y - 4} width={8} height={8} rx={1} fill="#facc15">
                    <title>
                      {t.name}
                      {t.loaded_item ? ` · ${t.loaded_item}` : ''}
                    </title>
                  </rect>
                );
              })}
              {snap.nodes.map((n) => {
                const p = nodePos[n.id];
                return (
                  <g key={n.id}>
                    <circle cx={p.x} cy={p.y} r={6} fill={NODE_COLOR[n.type] ?? '#94a3b8'} />
                    <text
                      x={p.x + 9}
                      y={p.y + 3}
                      fontSize={10}
                      fill="#cbd5e1"
                      pointerEvents="none"
                    >
                      {n.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Summary">
            <dl className="space-y-2 text-sm">
              <Row label="Routes" value={String(summary.route_count)} />
              <Row label="Nodes" value={String(summary.node_count)} />
              <Row
                label="Peak utilization"
                value={`${Math.round(summary.max_utilization * 100)}%`}
              />
            </dl>
            <div className="mt-3 space-y-1 border-t border-surface-border pt-2 text-xs">
              {Object.entries(summary.throughput_by_mode).map(([mode, total]) => (
                <div key={mode} className="flex justify-between text-slate-400">
                  <span>{MODE_LABEL[mode as LogisticsMode] ?? mode}</span>
                  <span className="tabular-nums">{formatPerMinute(total)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Card title="Routes">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="pb-2 font-medium">Route</th>
              <th className="pb-2 font-medium">Mode</th>
              <th className="pb-2 font-medium">Item</th>
              <th className="pb-2 text-right font-medium">Throughput</th>
              <th className="pb-2 text-right font-medium">Capacity</th>
              <th className="pb-2 font-medium">Utilization</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {snap.routes.map((r) => (
              <tr key={r.id}>
                <td className="py-2 text-slate-200">{r.name}</td>
                <td className="py-2 text-slate-400">{MODE_LABEL[r.mode]}</td>
                <td className="py-2 text-slate-400">{r.item}</td>
                <td className="py-2 text-right tabular-nums text-slate-300">
                  {formatPerMinute(r.throughput_per_min)}
                </td>
                <td className="py-2 text-right tabular-nums text-slate-500">
                  {formatPerMinute(r.capacity_per_min)}
                </td>
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-24 overflow-hidden rounded-full bg-surface-overlay">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, r.utilization * 100)}%`,
                          backgroundColor: utilizationColor(r.utilization),
                        }}
                      />
                    </div>
                    <span
                      className="tabular-nums text-xs"
                      style={{ color: utilizationColor(r.utilization) }}
                    >
                      {Math.round(r.utilization * 100)}%
                    </span>
                    {r.over_capacity && <StatusBadge kind="error" label="over" />}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-400">{label}</dt>
      <dd className="tabular-nums text-slate-100">{value}</dd>
    </div>
  );
}
