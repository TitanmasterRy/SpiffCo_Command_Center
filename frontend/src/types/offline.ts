/** Types mirroring `backend/app/schemas/offline.py`. */

export type BuildingCategory =
  | 'production'
  | 'extraction'
  | 'generator'
  | 'power_storage'
  | 'logistics';

export type DataSource = 'simulation' | 'frm' | 'save';

export interface BuildingCount {
  class_name: string;
  name: string;
  category: BuildingCategory;
  count: number;
  power_mw: number;
}

export interface SaveSummary {
  session_name: string;
  map_name: string;
  build_version: number;
  play_duration_seconds: number;
  saved_at: string | null;
  total_buildings: number;
  machine_count: number;
  generator_count: number;
  estimated_power_capacity_mw: number;
  estimated_power_consumption_mw: number;
  buildings: BuildingCount[];
}

export interface OfflineStatus {
  active: boolean;
  source: DataSource;
  save: SaveSummary | null;
}
