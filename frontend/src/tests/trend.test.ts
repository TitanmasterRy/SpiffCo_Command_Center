import { describe, expect, it } from 'vitest';
import type { Comparison } from '../types/analytics';
import { formatTrend } from '../utils/trend';

const cmp = (delta_percent: number | null): Comparison => ({
  current_avg: 0,
  previous_avg: 0,
  delta: 0,
  delta_percent,
});

describe('formatTrend', () => {
  it('shows an up arrow and signed percent for growth', () => {
    const t = formatTrend(cmp(0.12));
    expect(t.direction).toBe('up');
    expect(t.arrow).toBe('▲');
    expect(t.label).toBe('+12%');
  });

  it('shows a down arrow for decline', () => {
    const t = formatTrend(cmp(-0.3));
    expect(t.direction).toBe('down');
    expect(t.label).toBe('-30%');
  });

  it('treats tiny or null changes as flat', () => {
    expect(formatTrend(cmp(0.001)).direction).toBe('flat');
    expect(formatTrend(cmp(null)).label).toBe('—');
  });
});
