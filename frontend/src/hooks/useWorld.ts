import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { CustomMarkerIn, WorldSnapshot } from '../types/world';
import type { WsEnvelope } from '../types/api';
import { mergeWorldStream } from '../utils/worldStream';

const SNAPSHOT_KEY = ['world', 'snapshot'];
const MARKERS_KEY = ['world', 'markers'];

/** World snapshot (features + players); players stream in over WS. */
export function useWorld() {
  return useQuery({ queryKey: SNAPSHOT_KEY, queryFn: api.world.snapshot, staleTime: 60_000 });
}

/** Custom markers with create/delete mutations. */
export function useMarkers() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: MARKERS_KEY });
  const query = useQuery({ queryKey: MARKERS_KEY, queryFn: api.world.listMarkers });
  const create = useMutation({
    mutationFn: (marker: CustomMarkerIn) => api.world.createMarker(marker),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.world.deleteMarker(id),
    onSuccess: invalidate,
  });
  return { ...query, create, remove };
}

/**
 * Apply pushed world updates to the cached snapshot.
 *
 * `world.players` streams on every backend refresh; `world.features` arrives
 * only when feature state changed (artifact collected, miner installed, …) so
 * the map updates live without a page refresh.
 */
export function useWorldStreamHandler() {
  const queryClient = useQueryClient();
  return (message: WsEnvelope) => {
    if (message.topic !== 'world.players' && message.topic !== 'world.features') return;
    queryClient.setQueryData<WorldSnapshot>(SNAPSHOT_KEY, (snapshot) =>
      snapshot ? mergeWorldStream(snapshot, message) : snapshot,
    );
  };
}
