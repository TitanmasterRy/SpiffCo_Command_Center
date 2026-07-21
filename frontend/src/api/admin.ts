import { apiFetch } from './http';
import type {
  AdminState,
  BridgeActions,
  CheatCatalog,
  CheatExecuteResult,
  CheatLogEntry,
  PresetList,
  SpawnItemInfo,
} from '../types/admin';

/**
 * Typed functions for the admin cheat endpoints. The session token is attached
 * automatically by `apiFetch` (see `api/http.ts`); every endpoint here requires
 * the `use:admin-cheats` permission on the backend.
 */
export const adminApi = {
  catalog: () => apiFetch<CheatCatalog>('/api/v1/admin/catalog'),
  state: () => apiFetch<AdminState>('/api/v1/admin/state'),
  bridgeActions: () => apiFetch<BridgeActions>('/api/v1/admin/bridge-actions'),
  itemCatalog: () => apiFetch<SpawnItemInfo[]>('/api/v1/admin/item-catalog'),
  log: () => apiFetch<CheatLogEntry[]>('/api/v1/admin/log'),
  execute: (actionId: string, params: Record<string, unknown>) =>
    apiFetch<CheatExecuteResult>('/api/v1/admin/execute', {
      method: 'POST',
      body: JSON.stringify({ action_id: actionId, params }),
    }),
  getPresets: (kind: string) =>
    apiFetch<PresetList>(`/api/v1/admin/presets/${encodeURIComponent(kind)}`),
  putPresets: (kind: string, items: Record<string, unknown>[]) =>
    apiFetch<PresetList>(`/api/v1/admin/presets/${encodeURIComponent(kind)}`, {
      method: 'PUT',
      body: JSON.stringify({ kind, items }),
    }),
};
