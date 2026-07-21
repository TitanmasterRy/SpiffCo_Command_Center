import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../api/admin';
import { useAuth } from './useAuth';

/** True when the current user may use the cheat panel (gates its queries). */
function useCanCheat(): boolean {
  const { hasPermission } = useAuth();
  return hasPermission('use:admin-cheats');
}

/** The cheat catalog (static per session). */
export function useAdminCatalog() {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'catalog'],
    queryFn: adminApi.catalog,
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}

/** Server-tracked toggle states, refreshed after every execution. */
export function useAdminState() {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'state'],
    queryFn: adminApi.state,
    enabled,
    retry: false,
  });
}

/** Which cheats the connected game bridge actually implements. */
export function useBridgeActions() {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'bridge-actions'],
    queryFn: adminApi.bridgeActions,
    enabled,
    refetchInterval: 30_000,
    retry: false,
  });
}

/** The full in-game item catalogue for the spawn picker (static per session). */
export function useItemCatalog() {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'item-catalog'],
    queryFn: adminApi.itemCatalog,
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}

/** The admin command audit log (newest first). */
export function useAdminLog() {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'log'],
    queryFn: adminApi.log,
    enabled,
    refetchInterval: 15_000,
    retry: false,
  });
}

/** Execute one cheat action; refreshes toggle state and the log. */
export function useExecuteCheat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, params }: { actionId: string; params: Record<string, unknown> }) =>
      adminApi.execute(actionId, params),
    onSuccess: (result) => {
      queryClient.setQueryData(['admin', 'state'], { toggles: result.toggles });
      void queryClient.invalidateQueries({ queryKey: ['admin', 'log'] });
    },
  });
}

/** Saved presets of one kind (teleport locations, inventory presets, ...). */
export function useAdminPresets(kind: string) {
  const enabled = useCanCheat();
  return useQuery({
    queryKey: ['admin', 'presets', kind],
    queryFn: () => adminApi.getPresets(kind),
    enabled,
    retry: false,
  });
}

/** Replace the saved presets of one kind. */
export function useSaveAdminPresets(kind: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: Record<string, unknown>[]) => adminApi.putPresets(kind, items),
    onSuccess: (presets) => queryClient.setQueryData(['admin', 'presets', kind], presets),
  });
}
