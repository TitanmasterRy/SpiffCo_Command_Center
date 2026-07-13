import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api } from '../api/endpoints';
import type { BuildingInfo } from '../types/planner';

/** Static building catalog (footprints + costs); immutable, so cached forever. */
export function useBuildings() {
  return useQuery({
    queryKey: ['gamedata', 'buildings'],
    queryFn: api.gamedata.buildings,
    staleTime: Infinity,
  });
}

/** Building catalog indexed by id for O(1) lookup in the editor. */
export function useBuildingMap(): Record<string, BuildingInfo> {
  const { data } = useBuildings();
  return useMemo(() => Object.fromEntries((data ?? []).map((b) => [b.id, b])), [data]);
}
