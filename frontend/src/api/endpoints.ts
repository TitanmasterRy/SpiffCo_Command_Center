import type { AppInfo, HealthStatus, SettingValue } from '../types/api';
import type { DashboardSnapshot, PowerHistoryPoint } from '../types/dashboard';
import type {
  BuildingInfo,
  FactoryPlan,
  PlanCreate,
  PlanExport,
  PlanSummaryInfo,
  PlanUpdate,
  PlanVersion,
} from '../types/planner';
import type { CustomMarker, CustomMarkerIn, WorldSnapshot } from '../types/world';
import { apiFetch } from './http';

/** Typed functions for every backend endpoint, grouped by domain. */
export const api = {
  system: {
    health: () => apiFetch<HealthStatus>('/api/v1/health'),
    info: () => apiFetch<AppInfo>('/api/v1/info'),
    listSettings: () => apiFetch<SettingValue[]>('/api/v1/settings'),
    getSetting: (key: string) =>
      apiFetch<SettingValue>(`/api/v1/settings/${encodeURIComponent(key)}`),
    putSetting: (key: string, value: unknown) =>
      apiFetch<SettingValue>(`/api/v1/settings/${encodeURIComponent(key)}`, {
        method: 'PUT',
        body: JSON.stringify({ key, value }),
      }),
  },
  dashboard: {
    snapshot: () => apiFetch<DashboardSnapshot>('/api/v1/dashboard'),
    powerHistory: (limit = 120) =>
      apiFetch<PowerHistoryPoint[]>(`/api/v1/dashboard/history/power?limit=${limit}`),
  },
  world: {
    snapshot: () => apiFetch<WorldSnapshot>('/api/v1/world'),
    listMarkers: () => apiFetch<CustomMarker[]>('/api/v1/world/markers'),
    createMarker: (marker: CustomMarkerIn) =>
      apiFetch<CustomMarker>('/api/v1/world/markers', {
        method: 'POST',
        body: JSON.stringify(marker),
      }),
    deleteMarker: async (id: number) => {
      const response = await fetch(`/api/v1/world/markers/${id}`, { method: 'DELETE' });
      if (!response.ok && response.status !== 404) throw new Error('delete failed');
    },
  },
  gamedata: {
    buildings: () => apiFetch<BuildingInfo[]>('/api/v1/gamedata/buildings'),
  },
  plans: {
    list: () => apiFetch<PlanSummaryInfo[]>('/api/v1/plans'),
    get: (id: number) => apiFetch<FactoryPlan>(`/api/v1/plans/${id}`),
    create: (plan: PlanCreate) =>
      apiFetch<FactoryPlan>('/api/v1/plans', { method: 'POST', body: JSON.stringify(plan) }),
    update: (id: number, patch: PlanUpdate) =>
      apiFetch<FactoryPlan>(`/api/v1/plans/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
    remove: async (id: number) => {
      const response = await fetch(`/api/v1/plans/${id}`, { method: 'DELETE' });
      if (!response.ok && response.status !== 404) throw new Error('delete failed');
    },
    versions: (id: number) => apiFetch<PlanVersion[]>(`/api/v1/plans/${id}/versions`),
    revert: (id: number, version: number) =>
      apiFetch<FactoryPlan>(`/api/v1/plans/${id}/revert/${version}`, { method: 'POST' }),
    export: (id: number) => apiFetch<PlanExport>(`/api/v1/plans/${id}/export`),
    import: (doc: PlanExport) =>
      apiFetch<FactoryPlan>('/api/v1/plans/import', { method: 'POST', body: JSON.stringify(doc) }),
  },
};
