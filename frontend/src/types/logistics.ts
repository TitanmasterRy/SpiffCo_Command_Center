/** Mirrors of backend/app/schemas/logistics.py (Phase 6 — logistics). */

import type { Position } from './world';

export type LogisticsMode = 'belt' | 'pipe' | 'train' | 'truck' | 'drone';
export type NodeType = 'station' | 'factory' | 'port';

export interface BeltTier {
  id: string;
  name: string;
  rate: number;
}

export interface VehicleTier {
  id: string;
  name: string;
  capacity_slots: number | null;
  power_mw: number | null;
  fuel: string | null;
}

export interface TransportData {
  belts: BeltTier[];
  pipes: BeltTier[];
  vehicles: VehicleTier[];
}

export interface LogisticsNode {
  id: string;
  name: string;
  type: NodeType;
  position: Position;
}

export interface LogisticsRoute {
  id: string;
  name: string;
  mode: LogisticsMode;
  tier: string;
  item: string;
  throughput_per_min: number;
  capacity_per_min: number;
  from_node: string;
  to_node: string;
  /** Derived server-side: throughput / capacity. */
  utilization: number;
  /** Derived server-side: throughput > capacity. */
  over_capacity: boolean;
}

export interface TrainInfo {
  id: string;
  name: string;
  line: string;
  position: Position;
  loaded_item: string | null;
}

export interface LogisticsSummary {
  route_count: number;
  node_count: number;
  over_capacity_routes: string[];
  throughput_by_mode: Record<string, number>;
  max_utilization: number;
}

export interface LogisticsSnapshot {
  generated_at: string;
  source: 'simulation' | 'frm';
  nodes: LogisticsNode[];
  routes: LogisticsRoute[];
  trains: TrainInfo[];
  summary: LogisticsSummary;
}
