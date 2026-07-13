import { Card } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import { useAnalytics } from '../hooks/useAnalytics';
import type { Comparison } from '../types/analytics';
import { formatMegawatts, formatPerMinute } from '../utils/format';
import { formatTrend, type TrendDirection } from '../utils/trend';

const TREND_COLOR: Record<TrendDirection, string> = {
  up: '#199e70',
  down: '#e66767',
  flat: '#94a3b8',
};

function Trend({ comparison }: { comparison: Comparison }) {
  const t = formatTrend(comparison);
  return (
    <span className="tabular-nums" style={{ color: TREND_COLOR[t.direction] }}>
      {t.arrow} {t.label}
    </span>
  );
}

/** Analytics (Phase 9): power KPIs and busiest production lines over history. */
export default function Analytics() {
  const { data: summary, isLoading } = useAnalytics();

  if (isLoading || !summary) {
    return <p className="text-sm text-slate-500">Loading analytics…</p>;
  }

  const { power } = summary;
  const noData = power.sample_count === 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Analytics</h1>
        <StatusBadge kind="idle" label={`${power.sample_count} power samples`} />
      </div>

      {noData ? (
        <Card>
          <p className="text-sm text-slate-500">
            No history yet — telemetry is sampled every 30 seconds. Leave the app running,
            then return for trends and KPIs.
          </p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              title="Avg generation"
              value={formatMegawatts(power.produced.avg)}
              detail={`peak ${formatMegawatts(power.produced.max)}`}
            />
            <StatCard
              title="Avg consumption"
              value={formatMegawatts(power.consumed.avg)}
              detail={`peak ${formatMegawatts(power.consumed.max)}`}
            />
            <StatCard
              title="Uptime"
              value={`${Math.round(power.uptime_percent * 100)}%`}
              detail="samples with generation ≥ demand"
            />
            <StatCard
              title="Avg battery"
              value={`${Math.round(power.battery_avg * 100)}%`}
              detail="mean charge over window"
            />
          </div>

          <Card title="Generation trend">
            <div className="flex items-baseline gap-3 text-sm">
              <span className="text-slate-400">Recent vs. previous half of the window:</span>
              <Trend comparison={power.produced_trend} />
              <span className="text-xs text-slate-500">
                {formatMegawatts(power.produced_trend.previous_avg)} →{' '}
                {formatMegawatts(power.produced_trend.current_avg)}
              </span>
            </div>
          </Card>

          <Card title="Top production lines">
            {summary.top_production.length === 0 ? (
              <p className="text-sm text-slate-500">No production samples recorded yet.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
                    <th className="pb-2 font-medium">Item</th>
                    <th className="pb-2 text-right font-medium">Avg</th>
                    <th className="pb-2 text-right font-medium">Min</th>
                    <th className="pb-2 text-right font-medium">Max</th>
                    <th className="pb-2 text-right font-medium">Trend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {summary.top_production.map((p) => (
                    <tr key={p.item}>
                      <td className="py-2 text-slate-200">{p.name}</td>
                      <td className="py-2 text-right tabular-nums text-slate-300">
                        {formatPerMinute(p.rate.avg)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-500">
                        {formatPerMinute(p.rate.min)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-500">
                        {formatPerMinute(p.rate.max)}
                      </td>
                      <td className="py-2 text-right">
                        <Trend comparison={p.trend} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
