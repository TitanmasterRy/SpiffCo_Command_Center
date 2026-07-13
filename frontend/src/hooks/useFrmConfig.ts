import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { FrmConfig, FrmConfigStatus } from '../types/api';

/** Fetch the current FRM connection config and live connection state. */
export function useFrmConfig() {
  return useQuery({
    queryKey: ['system', 'frm-config'],
    queryFn: api.system.frmConfig,
    refetchInterval: 15_000,
  });
}

/** Apply an FRM config change; a reconnect swaps the live data source. */
export function useUpdateFrmConfig() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (config: FrmConfig) => api.system.updateFrmConfig(config),
    onSuccess: (status: FrmConfigStatus) => {
      client.setQueryData(['system', 'frm-config'], status);
      // A source swap changes every live view, mirroring an offline swap.
      for (const key of ['dashboard', 'world', 'logistics', 'power', 'analytics', 'advisor']) {
        void client.invalidateQueries({ queryKey: [key] });
      }
      void client.invalidateQueries({ queryKey: ['system', 'health'] });
      void client.invalidateQueries({ queryKey: ['offline', 'status'] });
    },
  });
}

/** Probe an FRM endpoint for reachability without saving it. */
export function useTestFrmConfig() {
  return useMutation({
    mutationFn: (config: FrmConfig) => api.system.testFrmConfig(config),
  });
}
