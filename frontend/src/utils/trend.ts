import type { Comparison } from '../types/analytics';

export type TrendDirection = 'up' | 'down' | 'flat';

export interface TrendDisplay {
  direction: TrendDirection;
  arrow: string;
  /** Signed percent text like "+12%", or "—" when unknown/flat. */
  label: string;
}

// Below this fractional change we treat a series as flat (avoids noisy arrows).
const FLAT_EPS = 0.005;

/** Format a recent-vs-previous comparison into an arrow + signed percent. */
export function formatTrend(comparison: Comparison): TrendDisplay {
  const pct = comparison.delta_percent;
  if (pct == null || Math.abs(pct) < FLAT_EPS) {
    return { direction: 'flat', arrow: '→', label: '—' };
  }
  const direction: TrendDirection = pct > 0 ? 'up' : 'down';
  const sign = pct > 0 ? '+' : '';
  return {
    direction,
    arrow: pct > 0 ? '▲' : '▼',
    label: `${sign}${Math.round(pct * 100)}%`,
  };
}
