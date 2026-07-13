import { useMemo, useRef, useState } from 'react';
import { Card } from '../components/Card';
import { api } from '../api/endpoints';
import { useBlueprintMutations, useBlueprints } from '../hooks/useBlueprints';
import type { BlueprintExport, BlueprintSummary } from '../types/blueprint';
import {
  DEFAULT_BLUEPRINT_FILTERS,
  deriveFacets,
  deriveStats,
  filterBlueprints,
  type BlueprintFilters,
} from '../utils/blueprintFilters';

function BlueprintCard({
  blueprint,
  onToggleFavorite,
  onExport,
  onDelete,
}: {
  blueprint: BlueprintSummary;
  onToggleFavorite: (b: BlueprintSummary) => void;
  onExport: (b: BlueprintSummary) => void;
  onDelete: (b: BlueprintSummary) => void;
}) {
  return (
    <section className="flex flex-col rounded-lg border border-surface-border bg-surface-raised p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate font-medium text-slate-100">{blueprint.name}</h3>
          <p className="text-xs uppercase tracking-widest text-slate-500">{blueprint.category}</p>
        </div>
        <button
          onClick={() => onToggleFavorite(blueprint)}
          className={`shrink-0 text-lg leading-none ${
            blueprint.favorite ? 'text-accent' : 'text-slate-600 hover:text-slate-400'
          }`}
          aria-label={blueprint.favorite ? 'Unfavorite' : 'Favorite'}
          title={blueprint.favorite ? 'Unfavorite' : 'Favorite'}
        >
          {blueprint.favorite ? '★' : '☆'}
        </button>
      </div>
      {blueprint.description && (
        <p className="mt-2 line-clamp-2 text-sm text-slate-400">{blueprint.description}</p>
      )}
      {blueprint.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {blueprint.tags.map((t) => (
            <span
              key={t}
              className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] text-slate-400"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3 flex gap-2 border-t border-surface-border pt-3">
        <button className="btn" onClick={() => onExport(blueprint)}>
          Export
        </button>
        <button className="btn text-status-error" onClick={() => onDelete(blueprint)}>
          Delete
        </button>
      </div>
    </section>
  );
}

/** Blueprint library (Phase 8): filter, favorite, import/export, statistics. */
export default function Blueprints() {
  const { data: blueprints = [], isLoading } = useBlueprints();
  const mutations = useBlueprintMutations();
  const [filters, setFilters] = useState<BlueprintFilters>(DEFAULT_BLUEPRINT_FILTERS);
  const fileInput = useRef<HTMLInputElement>(null);

  const facets = useMemo(() => deriveFacets(blueprints), [blueprints]);
  const stats = useMemo(() => deriveStats(blueprints), [blueprints]);
  const visible = useMemo(() => filterBlueprints(blueprints, filters), [blueprints, filters]);

  const patch = (key: keyof BlueprintFilters, value: string | boolean) =>
    setFilters((f) => ({ ...f, [key]: value }));

  const createBlueprint = () => {
    const name = window.prompt('New blueprint name', 'Untitled blueprint');
    if (!name) return;
    const category = window.prompt('Category', 'general') || 'general';
    mutations.create.mutate({ name, category });
  };

  const toggleFavorite = (b: BlueprintSummary) =>
    mutations.update.mutate({ id: b.id, patch: { favorite: !b.favorite } });

  const exportBlueprint = async (b: BlueprintSummary) => {
    const doc = await api.blueprints.export(b.id);
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${b.name.replace(/\s+/g, '-').toLowerCase()}.blueprint.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const deleteBlueprint = (b: BlueprintSummary) => {
    if (window.confirm(`Delete "${b.name}"?`)) mutations.remove.mutate(b.id);
  };

  const importBlueprint = async (file: File) => {
    try {
      const doc = JSON.parse(await file.text()) as BlueprintExport;
      mutations.importBlueprint.mutate(doc);
    } catch {
      window.alert('Could not import: file is not a valid blueprint document.');
    }
  };

  if (isLoading) return <p className="text-sm text-slate-500">Loading blueprints…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Blueprints</h1>
        <div className="flex items-center gap-2">
          <button className="btn" onClick={createBlueprint}>
            + New
          </button>
          <button className="btn" onClick={() => fileInput.current?.click()}>
            Import
          </button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && importBlueprint(e.target.files[0])}
          />
        </div>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-widest">Search</span>
            <input
              value={filters.search}
              onChange={(e) => patch('search', e.target.value)}
              placeholder="Name or description…"
              className="w-56 rounded border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-200"
            />
          </label>
          <label className="text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-widest">Category</span>
            <select
              value={filters.category}
              onChange={(e) => patch('category', e.target.value)}
              className="rounded border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="all">All</option>
              {facets.categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-widest">Tag</span>
            <select
              value={filters.tag}
              onChange={(e) => patch('tag', e.target.value)}
              className="rounded border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="all">All</option>
              {facets.tags.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 pb-1.5 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={filters.favoritesOnly}
              onChange={(e) => patch('favoritesOnly', e.target.checked)}
            />
            Favorites only
          </label>
          <span className="flex-1" />
          <div className="pb-1 text-xs text-slate-500">
            {stats.total} total · {stats.favorites} favorite ·{' '}
            {Object.keys(stats.by_category).length} categories
          </div>
        </div>
      </Card>

      {visible.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            {stats.total === 0
              ? 'No blueprints yet — create one or import a .blueprint.json file.'
              : 'No blueprints match the current filters.'}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visible.map((b) => (
            <BlueprintCard
              key={b.id}
              blueprint={b}
              onToggleFavorite={toggleFavorite}
              onExport={exportBlueprint}
              onDelete={deleteBlueprint}
            />
          ))}
        </div>
      )}
    </div>
  );
}
