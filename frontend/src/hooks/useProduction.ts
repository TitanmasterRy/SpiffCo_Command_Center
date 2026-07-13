import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api } from '../api/endpoints';
import type { ProductionRequest, RecipeInfo } from '../types/production';

/** All recipes (base + alternates); immutable, cached forever. */
export function useRecipes() {
  return useQuery({
    queryKey: ['gamedata', 'recipes'],
    queryFn: api.gamedata.recipes,
    staleTime: Infinity,
  });
}

/** All game items; immutable, cached forever. */
export function useItems() {
  return useQuery({
    queryKey: ['gamedata', 'items'],
    queryFn: api.gamedata.items,
    staleTime: Infinity,
  });
}

/** item id -> recipes that produce it (base recipes first). */
export function useProducibleRecipes(): Record<string, RecipeInfo[]> {
  const { data } = useRecipes();
  return useMemo(() => {
    const map: Record<string, RecipeInfo[]> = {};
    for (const recipe of data ?? []) {
      for (const out of recipe.outputs) (map[out.item] ??= []).push(recipe);
    }
    // Base recipes before alternates for stable default selection.
    for (const list of Object.values(map)) {
      list.sort((a, b) => Number(a.is_alternate) - Number(b.is_alternate));
    }
    return map;
  }, [data]);
}

/** Solve a production plan; disabled until a valid target+rate is supplied. */
export function useProductionPlan(request: ProductionRequest | null) {
  return useQuery({
    queryKey: ['production', 'plan', request],
    queryFn: () => api.production.plan(request as ProductionRequest),
    enabled: request != null && request.item !== '' && request.rate_per_min > 0,
    staleTime: Infinity,
  });
}
