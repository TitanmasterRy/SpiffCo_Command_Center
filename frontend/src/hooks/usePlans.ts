import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { PlanCreate, PlanExport, PlanUpdate } from '../types/planner';

const LIST_KEY = ['plans', 'list'];
const planKey = (id: number) => ['plans', 'detail', id];

/** Plan list (metadata only). */
export function usePlans() {
  return useQuery({ queryKey: LIST_KEY, queryFn: api.plans.list });
}

/** Full plan (layout + summary) for the selected id. */
export function usePlan(id: number | null) {
  return useQuery({
    queryKey: planKey(id ?? -1),
    queryFn: () => api.plans.get(id as number),
    enabled: id != null,
  });
}

/** Version history for the selected plan. */
export function usePlanVersions(id: number | null) {
  return useQuery({
    queryKey: ['plans', 'versions', id ?? -1],
    queryFn: () => api.plans.versions(id as number),
    enabled: id != null,
  });
}

/** All plan mutations, invalidating the affected caches on success. */
export function usePlanMutations() {
  const qc = useQueryClient();
  const invalidateAll = (id?: number) => {
    qc.invalidateQueries({ queryKey: LIST_KEY });
    if (id != null) {
      qc.invalidateQueries({ queryKey: planKey(id) });
      qc.invalidateQueries({ queryKey: ['plans', 'versions', id] });
    }
  };

  return {
    create: useMutation({
      mutationFn: (plan: PlanCreate) => api.plans.create(plan),
      onSuccess: (plan) => invalidateAll(plan.id),
    }),
    update: useMutation({
      mutationFn: ({ id, patch }: { id: number; patch: PlanUpdate }) => api.plans.update(id, patch),
      onSuccess: (plan) => invalidateAll(plan.id),
    }),
    remove: useMutation({
      mutationFn: (id: number) => api.plans.remove(id),
      onSuccess: () => invalidateAll(),
    }),
    revert: useMutation({
      mutationFn: ({ id, version }: { id: number; version: number }) =>
        api.plans.revert(id, version),
      onSuccess: (plan) => invalidateAll(plan.id),
    }),
    importPlan: useMutation({
      mutationFn: (doc: PlanExport) => api.plans.import(doc),
      onSuccess: (plan) => invalidateAll(plan.id),
    }),
  };
}
