/** Mirrors of backend/app/schemas/dashboard.py. */

export type Severity = 'info' | 'warning' | 'critical';
export type FactoryState = 'ok' | 'warn' | 'error' | 'idle';

export interface MachineSummary {
  total: number;
  running: number;
  idle: number;
  unpowered: number;
}

export interface FactoryStatus {
  id: string;
  name: string;
  status: FactoryState;
  efficiency: number;
  machines: MachineSummary;
}

export interface PowerStats {
  produced_mw: number;
  consumed_mw: number;
  capacity_mw: number;
  battery_percent: number;
  battery_capacity_mwh: number;
  fuse_triggered: boolean;
}

export interface ProductionStat {
  item: string;
  name: string;
  current_per_min: number;
  target_per_min: number;
}

export interface StorageLevel {
  item: string;
  name: string;
  stored: number;
  capacity: number;
}

export interface Alert {
  id: string;
  severity: Severity;
  title: string;
  message: string;
  source: string;
}

export interface DashboardSnapshot {
  generated_at: string;
  source: 'simulation' | 'frm';
  power: PowerStats;
  machines: MachineSummary;
  factories: FactoryStatus[];
  production: ProductionStat[];
  storage: StorageLevel[];
  alerts: Alert[];
}

export interface PowerHistoryPoint {
  timestamp: string;
  produced_mw: number;
  consumed_mw: number;
  capacity_mw: number;
  battery_percent: number;
}
