import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

/** Analytics summary (power KPIs + top production); refetches periodically. */
export function useAnalytics(limit = 240) {
  return useQuery({
    queryKey: ['analytics', 'summary', limit],
    queryFn: () => api.analytics.summary(limit),
    refetchInterval: 30_000,
  });
}
