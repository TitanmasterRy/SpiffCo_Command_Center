import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import type { BlueprintExport, BlueprintIn, BlueprintUpdate } from '../types/blueprint';

const LIST_KEY = ['blueprints', 'list'];

/** The full blueprint library (summaries); filtered client-side. */
export function useBlueprints() {
  return useQuery({ queryKey: LIST_KEY, queryFn: api.blueprints.list });
}

/** All blueprint mutations, invalidating the library on success. */
export function useBlueprintMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: LIST_KEY });
  return {
    create: useMutation({
      mutationFn: (blueprint: BlueprintIn) => api.blueprints.create(blueprint),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: ({ id, patch }: { id: number; patch: BlueprintUpdate }) =>
        api.blueprints.update(id, patch),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (id: number) => api.blueprints.remove(id),
      onSuccess: invalidate,
    }),
    importBlueprint: useMutation({
      mutationFn: (doc: BlueprintExport) => api.blueprints.import(doc),
      onSuccess: invalidate,
    }),
  };
}
