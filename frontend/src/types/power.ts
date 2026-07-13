/** Mirrors of backend/app/schemas/power.py (Phase 7 — power page). */

import type { PowerHistoryPoint, PowerStats, Severity } from './dashboard';

export type PowerStatus = 'ok' | 'warn' | 'critical';
export type BatteryTrend = 'charging' | 'draining' | 'stable';

export interface PowerBuildingInfo {
  id: string;
  name: string;
  power_mw: number;
  fuel: string | null;
  fuel_rate: number | null;
  requires_water: boolean;
  water_rate: number | null;
  capacity_mwh: number | null;
  max_charge_mw: number | null;
}

export interface BatteryStatus {
  percent: number;
  capacity_mwh: number;
  stored_mwh: number;
  trend: BatteryTrend;
  minutes_remaining: number | null;
}

export interface PowerRecommendation {
  severity: Severity;
  title: string;
  message: string;
}

export interface PowerReport {
  generated_at: string;
  source: 'simulation' | 'frm';
  power: PowerStats;
  headroom_mw: number;
  headroom_percent: number;
  status: PowerStatus;
  battery: BatteryStatus;
  recommendations: PowerRecommendation[];
  history: PowerHistoryPoint[];
}
