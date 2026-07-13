import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';

/** Poll backend health every 10s; used by the top bar and dashboard. */
export function useHealth() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: api.system.health,
    refetchInterval: 10_000,
  });
}

/** Fetch static app info once (name, version, environment). */
export function useAppInfo() {
  return useQuery({
    queryKey: ['system', 'info'],
    queryFn: api.system.info,
    staleTime: Infinity,
  });
}
