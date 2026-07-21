/** Types for the admin panel, mirroring `backend/app/schemas/admin.py`. */

export interface SessionInfo {
  token: string;
  username: string;
  expires_at: string;
}

export type ParamType = 'number' | 'slider' | 'text' | 'select' | 'item' | 'coords';
export type ControlType = 'button' | 'toggle';

export interface CheatParam {
  name: string;
  label: string;
  type: ParamType;
  options: string[] | null;
  min: number | null;
  max: number | null;
  step: number | null;
  default: unknown | null;
  unit: string | null;
}

export interface CheatAction {
  id: string;
  label: string;
  control: ControlType;
  params: CheatParam[];
  danger: boolean;
  hint: string | null;
  /** "player": targeted at one player (UI adds an online-player selector). */
  scope: 'player' | 'world';
  /** True when the action alters state shared by every player (badged). */
  affects_all: boolean;
}

export interface CheatSection {
  id: string;
  label: string;
  actions: CheatAction[];
}

export interface CheatCategory {
  id: string;
  label: string;
  icon: string;
  sections: CheatSection[];
}

export interface CheatCatalog {
  categories: CheatCategory[];
  executor: 'command_endpoint' | 'simulated';
  executor_hint: string;
}

export interface CheatExecuteResult {
  action_id: string;
  status: 'executed' | 'simulated';
  detail: string;
  toggles: Record<string, boolean>;
  response: Record<string, unknown>;
}

export interface CheatLogEntry {
  timestamp: string;
  username: string;
  action_id: string;
  params: Record<string, unknown>;
  status: string;
}

export interface AdminState {
  toggles: Record<string, boolean>;
}

/** Which catalog actions the connected game bridge can actually perform. */
export interface BridgeActions {
  executor: 'command_endpoint' | 'simulated';
  /** null = don't disable anything (simulated, or bridge unreachable). */
  supported: string[] | null;
}

/** One entry in the full in-game item catalogue (the spawn picker's source). */
export interface SpawnItemInfo {
  /** Game descriptor class (`Desc_IronPlate_C`) sent to the bridge to spawn it. */
  class_name: string;
  name: string;
  category: string;
  form: 'solid' | 'liquid' | 'gas';
  stack_size: number;
  sink_points: number;
}

export interface PresetList {
  kind: string;
  items: Record<string, unknown>[];
}
