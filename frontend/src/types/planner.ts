/** Mirrors of backend/app/schemas/planner.py (Phase 4 — factory planner). */

export type Rotation = 0 | 90 | 180 | 270;

export interface GridSpec {
  width: number;
  length: number;
  cell_cm: number;
}

export interface Placement {
  id: string;
  building: string;
  x: number;
  y: number;
  rotation: Rotation;
  clock: number;
}

export interface Layout {
  grid: GridSpec;
  placements: Placement[];
}

export interface PlanSummary {
  total_power_mw: number;
  machine_count: number;
  machine_counts: Record<string, number>;
  build_cost: Record<string, number>;
}

export interface PlanSummaryInfo {
  id: number;
  name: string;
  description: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface FactoryPlan extends PlanSummaryInfo {
  layout: Layout;
  summary: PlanSummary;
}

export interface PlanVersion {
  version: number;
  comment: string;
  created_at: string;
  layout: Layout;
}

export interface PlanCreate {
  name: string;
  description?: string;
  layout?: Layout;
}

export interface PlanUpdate {
  name?: string;
  description?: string;
  layout?: Layout;
  comment?: string;
}

export interface PlanExport {
  name: string;
  description?: string;
  layout: Layout;
  exported_at?: string | null;
}

export interface Footprint {
  width: number;
  length: number;
}

export interface BuildingInfo {
  id: string;
  name: string;
  category: string;
  power_mw: number;
  inputs: number;
  outputs: number;
  footprint: Footprint;
  build_cost: Record<string, number>;
}
