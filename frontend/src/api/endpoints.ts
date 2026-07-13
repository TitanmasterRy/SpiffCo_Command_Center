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
import type {
  Blueprint,
  BlueprintExport,
  BlueprintIn,
  BlueprintSummary,
  BlueprintUpdate,
} from '../types/blueprint';
import type { AnalyticsSummary, ProductionAnalytics } from '../types/analytics';
import type { LogisticsSnapshot, TransportData } from '../types/logistics';
import type { PowerBuildingInfo, PowerReport } from '../types/power';
import type { ItemInfo, ProductionPlan, ProductionRequest, RecipeInfo } from '../types/production';
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
    recipes: () => apiFetch<RecipeInfo[]>('/api/v1/gamedata/recipes'),
    items: () => apiFetch<ItemInfo[]>('/api/v1/gamedata/items'),
    transport: () => apiFetch<TransportData>('/api/v1/gamedata/transport'),
    powerBuildings: () => apiFetch<PowerBuildingInfo[]>('/api/v1/gamedata/power'),
  },
  logistics: {
    snapshot: () => apiFetch<LogisticsSnapshot>('/api/v1/logistics'),
  },
  power: {
    report: (history = 120) => apiFetch<PowerReport>(`/api/v1/power?history=${history}`),
  },
  analytics: {
    summary: (limit = 240) => apiFetch<AnalyticsSummary>(`/api/v1/analytics/summary?limit=${limit}`),
    production: (item: string, limit = 240) =>
      apiFetch<ProductionAnalytics>(
        `/api/v1/analytics/production/${encodeURIComponent(item)}?limit=${limit}`,
      ),
  },
  production: {
    plan: (request: ProductionRequest) =>
      apiFetch<ProductionPlan>('/api/v1/production/plan', {
        method: 'POST',
        body: JSON.stringify(request),
      }),
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
  blueprints: {
    list: () => apiFetch<BlueprintSummary[]>('/api/v1/blueprints'),
    get: (id: number) => apiFetch<Blueprint>(`/api/v1/blueprints/${id}`),
    create: (blueprint: BlueprintIn) =>
      apiFetch<Blueprint>('/api/v1/blueprints', { method: 'POST', body: JSON.stringify(blueprint) }),
    update: (id: number, patch: BlueprintUpdate) =>
      apiFetch<Blueprint>(`/api/v1/blueprints/${id}`, {
        method: 'PUT',
        body: JSON.stringify(patch),
      }),
    remove: async (id: number) => {
      const response = await fetch(`/api/v1/blueprints/${id}`, { method: 'DELETE' });
      if (!response.ok && response.status !== 404) throw new Error('delete failed');
    },
    export: (id: number) => apiFetch<BlueprintExport>(`/api/v1/blueprints/${id}/export`),
    import: (doc: BlueprintExport) =>
      apiFetch<Blueprint>('/api/v1/blueprints/import', {
        method: 'POST',
        body: JSON.stringify(doc),
      }),
  },
};
