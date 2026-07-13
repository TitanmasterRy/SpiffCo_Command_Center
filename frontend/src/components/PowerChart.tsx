import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PowerHistoryPoint } from '../types/dashboard';

/** Validated dark-surface categorical palette (dataviz skill, slots 1–2). */
const COLOR_PRODUCED = '#3987e5';
const COLOR_CONSUMED = '#199e70';
const INK_MUTED = '#7b8494';
const GRID = '#323945';

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Power history line chart: produced vs consumed with a capacity reference. */
export function PowerChart({ data }: { data: PowerHistoryPoint[] }) {
  if (data.length < 2) {
    return (
      <p className="py-10 text-center text-sm text-slate-500">
        Collecting history… samples are recorded every 30 seconds.
      </p>
    );
  }
  const capacity = data[data.length - 1].capacity_mw;
  const points = data.map((p) => ({ ...p, time: timeLabel(p.timestamp) }));

  return (
    <div className="h-64">
      <ResponsiveContainer>
        <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="time" stroke={INK_MUTED} tick={{ fontSize: 11 }} tickLine={false} />
          <YAxis
            stroke={INK_MUTED}
            tick={{ fontSize: 11 }}
            tickLine={false}
            width={48}
            domain={[0, Math.ceil(capacity * 1.1)]}
            unit=" MW"
          />
          <Tooltip
            contentStyle={{
              background: '#252a33',
              border: '1px solid #323945',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: '#cbd5e1' }}
            formatter={(value) => `${Number(value ?? 0).toFixed(1)} MW`}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine
            y={capacity}
            stroke={INK_MUTED}
            strokeDasharray="6 4"
            label={{ value: 'Capacity', fill: INK_MUTED, fontSize: 11, position: 'insideTopRight' }}
          />
          <Line
            type="monotone"
            dataKey="produced_mw"
            name="Produced"
            stroke={COLOR_PRODUCED}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="consumed_mw"
            name="Consumed"
            stroke={COLOR_CONSUMED}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
