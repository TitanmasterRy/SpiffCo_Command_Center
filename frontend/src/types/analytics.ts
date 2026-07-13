/** Mirrors of backend/app/schemas/analytics.py (Phase 9 — analytics). */

export interface SeriesStats {
  count: number;
  min: number;
  max: number;
  avg: number;
  latest: number;
}

export interface Comparison {
  current_avg: number;
  previous_avg: number;
  delta: number;
  delta_percent: number | null;
}

export interface PowerAnalytics {
  sample_count: number;
  produced: SeriesStats;
  consumed: SeriesStats;
  capacity: SeriesStats;
  battery_avg: number;
  uptime_percent: number;
  produced_trend: Comparison;
}

export interface ProductionAnalytics {
  item: string;
  name: string;
  sample_count: number;
  rate: SeriesStats;
  trend: Comparison;
}

export interface AnalyticsSummary {
  generated_at: string;
  sample_limit: number;
  power: PowerAnalytics;
  top_production: ProductionAnalytics[];
}
