import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { WsEnvelope } from '../types/api';
import type { LogisticsSnapshot, TrainInfo } from '../types/logistics';

const SNAPSHOT_KEY = ['logistics', 'snapshot'];

/** Logistics network snapshot; trains stream in over WS. */
export function useLogistics() {
  return useQuery({
    queryKey: SNAPSHOT_KEY,
    queryFn: api.logistics.snapshot,
    staleTime: 60_000,
  });
}

/** Apply pushed `logistics.trains` updates to the cached snapshot. */
export function useLogisticsStreamHandler() {
  const queryClient = useQueryClient();
  return (message: WsEnvelope) => {
    if (message.topic !== 'logistics.trains') return;
    queryClient.setQueryData<LogisticsSnapshot>(SNAPSHOT_KEY, (snapshot) =>
      snapshot ? { ...snapshot, trains: message.payload as TrainInfo[] } : snapshot,
    );
  };
}
