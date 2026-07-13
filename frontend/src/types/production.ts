/** Mirrors of backend/app/schemas/production.py (Phase 5 — production planner). */

export interface ItemRate {
  item: string;
  rate: number;
}

export interface RecipeInfo {
  id: string;
  name: string;
  machine: string;
  duration_seconds: number;
  inputs: ItemRate[];
  outputs: ItemRate[];
  is_alternate: boolean;
  unlock: string | null;
}

export interface ItemInfo {
  id: string;
  name: string;
  category: string;
  stack_size: number;
  is_fluid: boolean;
  sink_points: number;
}

export interface ProductionRequest {
  item: string;
  rate_per_min: number;
  recipe_overrides?: Record<string, string>;
  somersloop_items?: string[];
}

export interface ProductionNode {
  item: string;
  item_name: string;
  rate_per_min: number;
  is_raw: boolean;
  recipe_id: string | null;
  recipe_name: string | null;
  machine: string | null;
  machine_name: string | null;
  machine_count: number;
  power_mw: number;
  somersloop: boolean;
  byproducts: ItemRate[];
  inputs: ProductionNode[];
}

export interface ProductionTotals {
  power_mw: number;
  machine_counts: Record<string, number>;
  raw_materials: Record<string, number>;
  byproducts: Record<string, number>;
  build_cost: Record<string, number>;
}

export interface ProductionPlan {
  target: ItemRate;
  root: ProductionNode;
  totals: ProductionTotals;
  warnings: string[];
}
