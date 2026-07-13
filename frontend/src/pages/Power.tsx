import { Card } from '../components/Card';
import { Meter } from '../components/Meter';
import { PowerChart } from '../components/PowerChart';
import { StatCard } from '../components/StatCard';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { usePower } from '../hooks/usePower';
import type { PowerRecommendation, PowerStatus } from '../types/power';
import { formatMegawatts } from '../utils/format';

const STATUS_BADGE: Record<PowerStatus, { kind: StatusKind; label: string }> = {
  ok: { kind: 'ok', label: 'Healthy' },
  warn: { kind: 'warn', label: 'Low headroom' },
  critical: { kind: 'error', label: 'Over capacity' },
};

const SEVERITY_BADGE: Record<PowerRecommendation['severity'], { kind: StatusKind; label: string }> = {
  info: { kind: 'ok', label: 'OK' },
  warning: { kind: 'warn', label: 'Warning' },
  critical: { kind: 'error', label: 'Critical' },
};

const TREND_LABEL = {
  charging: '▲ charging',
  draining: '▼ draining',
  stable: '● stable',
} as const;

/** Power page (Phase 7): generation vs. consumption, battery, and advice. */
export default function Power() {
  const { data: report, isLoading } = usePower();

  if (isLoading || !report) {
    return <p className="text-sm text-slate-500">Loading power…</p>;
  }

  const { power, battery } = report;
  const status = STATUS_BADGE[report.status];
  const minutes = battery.minutes_remaining;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Power</h1>
        <div className="flex items-center gap-2">
          {report.source === 'simulation' && (
            <StatusBadge kind="idle" label="Simulated — FRM arrives in Phase 11" />
          )}
          <StatusBadge kind={status.kind} label={status.label} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Generation"
          value={formatMegawatts(power.produced_mw)}
          detail={`${formatMegawatts(power.capacity_mw)} capacity`}
        />
        <StatCard
          title="Consumption"
          value={formatMegawatts(power.consumed_mw)}
          detail={power.fuse_triggered ? 'Fuse tripped!' : 'Grid nominal'}
        />
        <StatCard
          title="Headroom"
          value={formatMegawatts(report.headroom_mw)}
          detail={`${Math.round(report.headroom_percent * 100)}% of capacity`}
        />
        <StatCard
          title="Battery"
          value={`${Math.round(battery.percent * 100)}%`}
          detail={`${TREND_LABEL[battery.trend]}${
            minutes != null ? ` · ~${Math.round(minutes)} min` : ''
          }`}
        />
      </div>

      <Card title="Generation vs. consumption">
        <PowerChart data={report.history} />
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Grid load">
          <div className="space-y-3">
            <Meter
              label="Consumption vs. capacity"
              value={power.consumed_mw}
              max={power.capacity_mw}
              display={`${formatMegawatts(power.consumed_mw)} of ${formatMegawatts(power.capacity_mw)}`}
            />
            <Meter
              label="Battery charge"
              value={battery.stored_mwh}
              max={battery.capacity_mwh}
              display={`${battery.stored_mwh.toFixed(0)} / ${battery.capacity_mwh.toFixed(0)} MWh`}
            />
          </div>
        </Card>

        <Card title="Recommendations">
          <ul className="divide-y divide-surface-border">
            {report.recommendations.map((rec) => {
              const badge = SEVERITY_BADGE[rec.severity];
              return (
                <li key={rec.title} className="flex items-start gap-3 py-2">
                  <StatusBadge kind={badge.kind} label={badge.label} />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200">{rec.title}</p>
                    <p className="text-xs text-slate-500">{rec.message}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}
