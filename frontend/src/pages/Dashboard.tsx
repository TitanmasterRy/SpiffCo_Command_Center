import { Card } from '../components/Card';
import { Meter } from '../components/Meter';
import { PowerChart } from '../components/PowerChart';
import { StatCard } from '../components/StatCard';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useDashboard, usePowerHistory } from '../hooks/useDashboard';
import type { Alert, FactoryState, Severity } from '../types/dashboard';
import { formatMegawatts, formatPerMinute } from '../utils/format';

const FACTORY_BADGE: Record<FactoryState, StatusKind> = {
  ok: 'ok',
  warn: 'warn',
  error: 'error',
  idle: 'idle',
};

const SEVERITY_BADGE: Record<Severity, { kind: StatusKind; label: string }> = {
  info: { kind: 'idle', label: 'Info' },
  warning: { kind: 'warn', label: 'Warning' },
  critical: { kind: 'error', label: 'Critical' },
};

function AlertRow({ alert }: { alert: Alert }) {
  const badge = SEVERITY_BADGE[alert.severity];
  return (
    <li className="flex items-start gap-3 py-2">
      <StatusBadge kind={badge.kind} label={badge.label} />
      <div className="min-w-0">
        <p className="text-sm text-slate-200">{alert.title}</p>
        <p className="text-xs text-slate-500">{alert.message}</p>
      </div>
    </li>
  );
}

/** Live operations dashboard (Phase 2), fed by WebSocket snapshots. */
export default function Dashboard() {
  const { data: snap, isLoading } = useDashboard();
  const { data: history } = usePowerHistory();

  if (isLoading || !snap) {
    return <p className="text-sm text-slate-500">Loading dashboard…</p>;
  }

  const { power, machines } = snap;
  const overallEff =
    snap.factories.reduce((sum, f) => sum + f.efficiency, 0) / (snap.factories.length || 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Dashboard</h1>
        {snap.source === 'simulation' && (
          <StatusBadge kind="idle" label="Simulated data — FRM arrives in Phase 11" />
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Power"
          value={formatMegawatts(power.produced_mw)}
          detail={`${formatMegawatts(power.consumed_mw)} consumed · ${formatMegawatts(power.capacity_mw)} capacity`}
        />
        <StatCard
          title="Battery"
          value={`${Math.round(power.battery_percent * 100)}%`}
          detail={`${power.battery_capacity_mwh.toFixed(0)} MWh capacity`}
        />
        <StatCard
          title="Machines"
          value={`${machines.running}/${machines.total}`}
          detail={`${machines.idle} idle · ${machines.unpowered} unpowered`}
        />
        <StatCard
          title="Efficiency"
          value={`${Math.round(overallEff * 100)}%`}
          detail={`${snap.alerts.length} active alert${snap.alerts.length === 1 ? '' : 's'}`}
        />
      </div>

      <Card title="Power — last hour">
        <PowerChart data={history ?? []} />
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Factories">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="pb-2 font-medium">Factory</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 text-right font-medium">Machines</th>
                <th className="pb-2 text-right font-medium">Efficiency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {snap.factories.map((f) => (
                <tr key={f.id}>
                  <td className="py-2 text-slate-200">{f.name}</td>
                  <td className="py-2">
                    <StatusBadge kind={FACTORY_BADGE[f.status]} label={f.status.toUpperCase()} />
                  </td>
                  <td className="py-2 text-right tabular-nums text-slate-300">
                    {f.machines.running}/{f.machines.total}
                  </td>
                  <td className="py-2 text-right tabular-nums text-slate-300">
                    {Math.round(f.efficiency * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Production vs target">
          <div className="space-y-3">
            {snap.production.map((p) => (
              <Meter
                key={p.item}
                label={p.name}
                value={p.current_per_min}
                max={p.target_per_min}
                display={`${formatPerMinute(p.current_per_min)} of ${formatPerMinute(p.target_per_min)}`}
              />
            ))}
          </div>
        </Card>

        <Card title="Storage">
          <div className="space-y-3">
            {snap.storage.map((s) => (
              <Meter
                key={s.item}
                label={s.name}
                value={s.stored}
                max={s.capacity}
                display={`${s.stored.toFixed(0)} / ${s.capacity.toFixed(0)}`}
              />
            ))}
          </div>
        </Card>

        <Card title="Alerts">
          {snap.alerts.length === 0 ? (
            <p className="text-sm text-slate-500">No active alerts. Factory nominal.</p>
          ) : (
            <ul className="divide-y divide-surface-border">
              {snap.alerts.map((a) => (
                <AlertRow key={a.id} alert={a} />
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
