import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

/** Advisor report (ranked findings); refetches on the dashboard cadence. */
export function useAdvisor() {
  return useQuery({
    queryKey: ['advisor', 'report'],
    queryFn: api.advisor.report,
    refetchInterval: 15_000,
  });
}
