import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { DashboardSnapshot, WsEnvelope } from '../types/api-all';

/** Live dashboard snapshot: fetched once, then updated by WebSocket pushes. */
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'snapshot'],
    queryFn: api.dashboard.snapshot,
    refetchInterval: 15_000, // safety net if the WS stream drops
  });
}

/** Recent power samples for the history chart (refreshed with the 30s sampler). */
export function usePowerHistory(limit = 120) {
  return useQuery({
    queryKey: ['dashboard', 'power-history', limit],
    queryFn: () => api.dashboard.powerHistory(limit),
    refetchInterval: 30_000,
  });
}

/** Apply a pushed snapshot to the query cache (called from the WS stream). */
export function useDashboardStreamHandler() {
  const queryClient = useQueryClient();
  return (message: WsEnvelope) => {
    if (message.topic === 'dashboard.snapshot') {
      queryClient.setQueryData(['dashboard', 'snapshot'], message.payload as DashboardSnapshot);
    }
  };
}
