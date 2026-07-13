import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { WsEnvelope } from '../types/api';
import type { PowerReport } from '../types/power';
import type { PowerStats } from '../types/dashboard';

const REPORT_KEY = ['power', 'report'];

/** Power report: live grid stats + analysis + history. Refetches on interval. */
export function usePower() {
  return useQuery({
    queryKey: REPORT_KEY,
    queryFn: () => api.power.report(),
    refetchInterval: 15_000,
  });
}

/**
 * Patch the cached report's live `power` stats from `dashboard.snapshot` frames
 * so the headroom/battery tiles stay live between refetches. Derived analysis
 * fields refresh on the next fetch.
 */
export function usePowerStreamHandler() {
  const queryClient = useQueryClient();
  return (message: WsEnvelope) => {
    if (message.topic !== 'dashboard.snapshot') return;
    const payload = message.payload as { power?: PowerStats };
    if (!payload.power) return;
    queryClient.setQueryData<PowerReport>(REPORT_KEY, (report) =>
      report ? { ...report, power: payload.power as PowerStats } : report,
    );
  };
}
