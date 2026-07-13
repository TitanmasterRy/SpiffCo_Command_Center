import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { OfflineStatus } from '../types/offline';

/** Poll the active data source (simulation / FRM / save file). */
export function useOfflineStatus() {
  return useQuery({
    queryKey: ['offline', 'status'],
    queryFn: api.offline.status,
    refetchInterval: 15_000,
  });
}

/** Invalidate every server-state query after the data source changes. */
function useResourceRefresh() {
  const client = useQueryClient();
  return (status: OfflineStatus) => {
    client.setQueryData(['offline', 'status'], status);
    // A source swap changes dashboard/world/logistics/power/analytics/advisor.
    for (const key of ['dashboard', 'world', 'logistics', 'power', 'analytics', 'advisor']) {
      void client.invalidateQueries({ queryKey: [key] });
    }
    void client.invalidateQueries({ queryKey: ['system', 'health'] });
  };
}

/** Upload a `.sav` file and make it the live data source. */
export function useUploadSave() {
  const refresh = useResourceRefresh();
  return useMutation({
    mutationFn: (file: File) => api.offline.uploadSave(file),
    onSuccess: refresh,
  });
}

/** Unload the save and restore simulation/FRM. */
export function useClearSave() {
  const refresh = useResourceRefresh();
  return useMutation({
    mutationFn: () => api.offline.clearSave(),
    onSuccess: refresh,
  });
}
