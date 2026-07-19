/** Mirrors of backend/app/schemas/world.py. */

export type FeatureType =
  | 'factory'
  | 'resource_node'
  | 'resource_well'
  | 'geyser'
  | 'power_plant'
  | 'train_station'
  | 'drone_port'
  | 'truck_station'
  | 'artifact'
  | 'collectible'
  | 'wreck';

export interface Position {
  x: number;
  y: number;
  z: number;
}

export interface MapFeature {
  id: string;
  type: FeatureType;
  name: string;
  position: Position;
  meta: Record<string, string | number>;
  /** Pickups only: already collected by a player. */
  collected: boolean | null;
  /** Resource nodes only: an extractor is installed. */
  occupied: boolean | null;
}

export interface PlayerInfo {
  id: string;
  name: string;
  position: Position;
  online: boolean;
}

/** A conveyor belt segment rendered as a polyline on the map. */
export interface BeltPath {
  id: string;
  name: string;
  /** Short UE class, e.g. Build_ConveyorBeltMk1_C. */
  class_name: string;
  /** Spline points in cm. */
  points: Position[];
  items_per_minute: number | null;
}

export interface WorldSnapshot {
  generated_at: string;
  source: 'simulation' | 'frm' | 'save';
  players: PlayerInfo[];
  features: MapFeature[];
  belts: BeltPath[];
  /** Power lines (straight segments). */
  cables: BeltPath[];
  /** Pipeline splines. */
  pipes: BeltPath[];
}

export interface CustomMarkerIn {
  name: string;
  icon?: string;
  color?: string;
  position: Position;
  notes?: string;
}

export interface CustomMarker extends Required<CustomMarkerIn> {
  id: number;
}
