import { Card } from '../components/Card';
import { Meter } from '../components/Meter';
import { StatCard } from '../components/StatCard';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useDashboard } from '../hooks/useDashboard';
import type { FactoryState, FactoryStatus } from '../types/dashboard';

const FACTORY_BADGE: Record<FactoryState, StatusKind> = {
  ok: 'ok',
  warn: 'warn',
  error: 'error',
  idle: 'idle',
};

function FactoryCard({ factory }: { factory: FactoryStatus }) {
  const { machines } = factory;
  return (
    <Card title={factory.name}>
      <div className="space-y-4">
        <div className="-mt-1">
          <StatusBadge kind={FACTORY_BADGE[factory.status]} label={factory.status.toUpperCase()} />
        </div>
        <Meter
          label="Efficiency"
          value={factory.efficiency}
          max={1}
          display={`${Math.round(factory.efficiency * 100)}%`}
        />
        <div className="grid grid-cols-4 gap-2 text-center">
          <div>
            <p className="text-lg font-semibold tabular-nums text-slate-100">{machines.total}</p>
            <p className="text-xs uppercase tracking-wider text-slate-500">Total</p>
          </div>
          <div>
            <p className="text-lg font-semibold tabular-nums text-emerald-400">{machines.running}</p>
            <p className="text-xs uppercase tracking-wider text-slate-500">Running</p>
          </div>
          <div>
            <p className="text-lg font-semibold tabular-nums text-amber-400">{machines.idle}</p>
            <p className="text-xs uppercase tracking-wider text-slate-500">Idle</p>
          </div>
          <div>
            <p className="text-lg font-semibold tabular-nums text-rose-400">{machines.unpowered}</p>
            <p className="text-xs uppercase tracking-wider text-slate-500">Unpowered</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

/** Per-factory operations view (status, machine counts, efficiency), fed by dashboard snapshots. */
export default function Factories() {
  const { data: snap, isLoading } = useDashboard();

  if (isLoading || !snap) {
    return <p className="text-sm text-slate-500">Loading factories…</p>;
  }

  const factories = snap.factories;
  const totals = factories.reduce(
    (acc, f) => ({
      total: acc.total + f.machines.total,
      running: acc.running + f.machines.running,
      idle: acc.idle + f.machines.idle,
      unpowered: acc.unpowered + f.machines.unpowered,
    }),
    { total: 0, running: 0, idle: 0, unpowered: 0 },
  );
  const overallEff =
    factories.reduce((sum, f) => sum + f.efficiency, 0) / (factories.length || 1);
  const needsAttention = factories.filter((f) => f.status === 'warn' || f.status === 'error').length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Factories</h1>
        {snap.source === 'simulation' && (
          <StatusBadge kind="idle" label="Simulated data — FRM arrives in Phase 11" />
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Factories"
          value={`${factories.length}`}
          detail={`${needsAttention} need${needsAttention === 1 ? 's' : ''} attention`}
        />
        <StatCard
          title="Machines"
          value={`${totals.running}/${totals.total}`}
          detail={`${totals.idle} idle · ${totals.unpowered} unpowered`}
        />
        <StatCard title="Avg efficiency" value={`${Math.round(overallEff * 100)}%`} detail="across all factories" />
        <StatCard
          title="Unpowered"
          value={`${totals.unpowered}`}
          detail={totals.unpowered === 0 ? 'all machines powered' : 'machines offline'}
        />
      </div>

      {factories.length === 0 ? (
        <Card title="Factories">
          <p className="text-sm text-slate-500">No factories reported yet.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {factories.map((f) => (
            <FactoryCard key={f.id} factory={f} />
          ))}
        </div>
      )}
    </div>
  );
}
