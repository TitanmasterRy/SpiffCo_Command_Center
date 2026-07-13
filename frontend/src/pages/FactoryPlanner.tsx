import { useEffect, useMemo, useRef, useState } from 'react';
import { Card } from '../components/Card';
import { PlannerCanvas } from '../components/PlannerCanvas';
import { StatusBadge } from '../components/StatusBadge';
import { useBuildingMap, useBuildings } from '../hooks/useGameData';
import { usePlan, usePlanMutations, usePlanVersions, usePlans } from '../hooks/usePlans';
import type { Layout, Placement, PlanExport } from '../types/planner';
import { formatMegawatts } from '../utils/format';
import { invalidPlacementIds, nextRotation, placementPower } from '../utils/plannerGrid';

const EMPTY_LAYOUT: Layout = { grid: { width: 40, length: 40, cell_cm: 100 }, placements: [] };

/** Stable id for a new placement. */
function newPlacementId(): string {
  return `p-${crypto.randomUUID().slice(0, 8)}`;
}

/** Local rollup (power/counts/cost) so the summary updates before a save. */
function useLocalSummary(layout: Layout, buildings: ReturnType<typeof useBuildingMap>) {
  return useMemo(() => {
    let power = 0;
    const counts: Record<string, number> = {};
    const cost: Record<string, number> = {};
    for (const p of layout.placements) {
      const b = buildings[p.building];
      if (!b) continue;
      power += placementPower(b, p.clock);
      counts[b.id] = (counts[b.id] ?? 0) + 1;
      for (const [item, qty] of Object.entries(b.build_cost)) cost[item] = (cost[item] ?? 0) + qty;
    }
    return { power, counts, cost, machineCount: layout.placements.length };
  }, [layout, buildings]);
}

export default function FactoryPlanner() {
  const { data: plans } = usePlans();
  const { isLoading: buildingsLoading } = useBuildings();
  const buildingMap = useBuildingMap();
  const buildingList = useMemo(() => Object.values(buildingMap), [buildingMap]);
  const mutations = usePlanMutations();

  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const { data: plan } = usePlan(selectedPlanId);
  const { data: versions } = usePlanVersions(selectedPlanId);

  const [draft, setDraft] = useState<Layout>(EMPTY_LAYOUT);
  const [tool, setTool] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Auto-select the first plan once the list loads.
  useEffect(() => {
    if (selectedPlanId == null && plans && plans.length > 0) setSelectedPlanId(plans[0].id);
  }, [plans, selectedPlanId]);

  // Reset the draft whenever the loaded plan or its version changes.
  useEffect(() => {
    if (plan) {
      setDraft(structuredClone(plan.layout));
      setSelectedId(null);
    }
  }, [plan?.id, plan?.version]);

  const invalidIds = useMemo(() => invalidPlacementIds(draft, buildingMap), [draft, buildingMap]);
  const summary = useLocalSummary(draft, buildingMap);
  const dirty = plan != null && JSON.stringify(draft) !== JSON.stringify(plan.layout);
  const selectedPlacement = draft.placements.find((p) => p.id === selectedId) ?? null;

  const mutate = (fn: (placements: Placement[]) => Placement[]) =>
    setDraft((d) => ({ ...d, placements: fn(d.placements) }));

  const place = (x: number, y: number) => {
    if (!tool) return;
    const id = newPlacementId();
    mutate((ps) => [...ps, { id, building: tool, x, y, rotation: 0, clock: 1 }]);
    setSelectedId(id);
  };

  const move = (id: string, x: number, y: number) =>
    mutate((ps) => ps.map((p) => (p.id === id ? { ...p, x, y } : p)));

  const rotateSelected = () =>
    selectedId &&
    mutate((ps) =>
      ps.map((p) => (p.id === selectedId ? { ...p, rotation: nextRotation(p.rotation) } : p)),
    );

  const deleteSelected = () => {
    if (!selectedId) return;
    mutate((ps) => ps.filter((p) => p.id !== selectedId));
    setSelectedId(null);
  };

  const setClock = (clock: number) =>
    selectedId && mutate((ps) => ps.map((p) => (p.id === selectedId ? { ...p, clock } : p)));

  const setGrid = (key: 'width' | 'length', value: number) =>
    setDraft((d) => ({ ...d, grid: { ...d.grid, [key]: Math.max(1, Math.min(1000, value)) } }));

  // Keyboard shortcuts (ignored while typing in an input).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (e.key === '?') setShowHelp((s) => !s);
      else if (e.key === 'Escape') {
        setTool(null);
        setSelectedId(null);
        setShowHelp(false);
      } else if (e.key === 'r' || e.key === 'R') rotateSelected();
      else if (e.key === 'Delete' || e.key === 'Backspace') deleteSelected();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  const save = () => {
    if (selectedPlanId == null || !dirty) return;
    mutations.update.mutate({ id: selectedPlanId, patch: { layout: draft, comment: 'edit' } });
  };

  const createPlan = () => {
    const name = window.prompt('New plan name', 'Untitled plan');
    if (!name) return;
    mutations.create.mutate(
      { name, layout: EMPTY_LAYOUT },
      { onSuccess: (p) => setSelectedPlanId(p.id) },
    );
  };

  const renamePlan = () => {
    if (!plan) return;
    const name = window.prompt('Rename plan', plan.name);
    if (name) mutations.update.mutate({ id: plan.id, patch: { name } });
  };

  const duplicatePlan = () => {
    if (!plan) return;
    mutations.create.mutate(
      { name: `${plan.name} (copy)`, description: plan.description, layout: draft },
      { onSuccess: (p) => setSelectedPlanId(p.id) },
    );
  };

  const deletePlan = () => {
    if (!plan || !window.confirm(`Delete "${plan.name}"? This cannot be undone.`)) return;
    mutations.remove.mutate(plan.id, { onSuccess: () => setSelectedPlanId(null) });
  };

  const revert = (version: number) => {
    if (selectedPlanId != null) mutations.revert.mutate({ id: selectedPlanId, version });
  };

  const exportPlan = () => {
    if (!plan) return;
    const doc: PlanExport = { name: plan.name, description: plan.description, layout: draft };
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${plan.name.replace(/\s+/g, '-').toLowerCase()}.plan.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importPlan = async (file: File) => {
    try {
      const doc = JSON.parse(await file.text()) as PlanExport;
      mutations.importPlan.mutate(doc, { onSuccess: (p) => setSelectedPlanId(p.id) });
    } catch {
      window.alert('Could not import: file is not a valid plan document.');
    }
  };

  if (buildingsLoading) return <p className="text-sm text-slate-500">Loading planner…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Factory Planner</h1>
        <div className="flex items-center gap-2">
          {dirty && <StatusBadge kind="warn" label="Unsaved changes" />}
          {invalidIds.size > 0 && (
            <StatusBadge kind="error" label={`${invalidIds.size} invalid`} />
          )}
          <button className="btn" onClick={() => setShowHelp(true)} aria-label="Keyboard help">
            ?
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[16rem_1fr_18rem]">
        {/* Plan list + palette */}
        <div className="space-y-4">
          <Card title="Plans">
            <div className="mb-2 flex gap-2">
              <button className="btn flex-1" onClick={createPlan}>
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
                onChange={(e) => e.target.files?.[0] && importPlan(e.target.files[0])}
              />
            </div>
            <ul className="space-y-0.5">
              {(plans ?? []).map((p) => (
                <li key={p.id}>
                  <button
                    onClick={() => setSelectedPlanId(p.id)}
                    className={`w-full truncate rounded px-2 py-1.5 text-left text-sm ${
                      p.id === selectedPlanId
                        ? 'bg-accent/10 text-accent'
                        : 'text-slate-300 hover:bg-surface-overlay'
                    }`}
                  >
                    {p.name}
                    <span className="ml-1 text-xs text-slate-500">v{p.version}</span>
                  </button>
                </li>
              ))}
              {(plans ?? []).length === 0 && (
                <li className="px-2 py-1.5 text-sm text-slate-500">No plans yet — create one.</li>
              )}
            </ul>
          </Card>

          <Card title="Buildings">
            <p className="mb-2 text-xs text-slate-500">Select, then click the grid to place.</p>
            <div className="space-y-0.5">
              {buildingList.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setTool(tool === b.id ? null : b.id)}
                  className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm ${
                    tool === b.id
                      ? 'bg-accent/10 text-accent'
                      : 'text-slate-300 hover:bg-surface-overlay'
                  }`}
                >
                  <span className="truncate">{b.name}</span>
                  <span className="ml-2 shrink-0 text-xs text-slate-500">
                    {b.footprint.width}×{b.footprint.length}
                  </span>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Canvas + toolbar */}
        <div className="space-y-3">
          {plan ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="mr-1 font-mono text-sm text-slate-200">{plan.name}</span>
                <button className="btn" onClick={renamePlan}>
                  Rename
                </button>
                <button className="btn" onClick={duplicatePlan}>
                  Duplicate
                </button>
                <button className="btn" onClick={exportPlan}>
                  Export
                </button>
                <button className="btn text-status-error" onClick={deletePlan}>
                  Delete
                </button>
                <span className="mx-1 h-4 w-px bg-surface-border" />
                <label className="flex items-center gap-1 text-xs text-slate-400">
                  W
                  <input
                    type="number"
                    min={1}
                    max={1000}
                    value={draft.grid.width}
                    onChange={(e) => setGrid('width', Number(e.target.value))}
                    className="w-16 rounded border border-surface-border bg-surface px-1 py-0.5 text-slate-200"
                  />
                </label>
                <label className="flex items-center gap-1 text-xs text-slate-400">
                  L
                  <input
                    type="number"
                    min={1}
                    max={1000}
                    value={draft.grid.length}
                    onChange={(e) => setGrid('length', Number(e.target.value))}
                    className="w-16 rounded border border-surface-border bg-surface px-1 py-0.5 text-slate-200"
                  />
                </label>
                <span className="flex-1" />
                <button
                  className="btn bg-accent/20 text-accent disabled:opacity-40"
                  onClick={save}
                  disabled={!dirty || invalidIds.size > 0}
                >
                  Save
                </button>
              </div>

              <PlannerCanvas
                layout={draft}
                buildings={buildingMap}
                invalidIds={invalidIds}
                selectedId={selectedId}
                tool={tool}
                onPlace={place}
                onSelect={setSelectedId}
                onMove={move}
              />

              {selectedPlacement && (
                <div className="flex flex-wrap items-center gap-3 rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-sm">
                  <span className="text-slate-200">
                    {buildingMap[selectedPlacement.building]?.name ?? selectedPlacement.building}
                  </span>
                  <span className="text-xs text-slate-500">
                    @ ({selectedPlacement.x}, {selectedPlacement.y}) · {selectedPlacement.rotation}°
                  </span>
                  <button className="btn" onClick={rotateSelected}>
                    Rotate (R)
                  </button>
                  <label className="flex items-center gap-1 text-xs text-slate-400">
                    Clock
                    <input
                      type="number"
                      min={1}
                      max={250}
                      step={5}
                      value={Math.round(selectedPlacement.clock * 100)}
                      onChange={(e) => setClock(Math.max(1, Math.min(250, Number(e.target.value))) / 100)}
                      className="w-16 rounded border border-surface-border bg-surface px-1 py-0.5 text-slate-200"
                    />
                    %
                  </label>
                  <button className="btn text-status-error" onClick={deleteSelected}>
                    Delete (Del)
                  </button>
                </div>
              )}
            </>
          ) : (
            <Card>
              <p className="text-sm text-slate-400">
                Select a plan on the left, or create a new one to start designing a layout.
              </p>
            </Card>
          )}
        </div>

        {/* Summary + versions */}
        <div className="space-y-4">
          <Card title="Summary">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-400">Power draw</dt>
                <dd className="tabular-nums text-slate-100">{formatMegawatts(summary.power)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Machines</dt>
                <dd className="tabular-nums text-slate-100">{summary.machineCount}</dd>
              </div>
            </dl>
            {Object.keys(summary.counts).length > 0 && (
              <div className="mt-3 space-y-1 border-t border-surface-border pt-2 text-xs">
                {Object.entries(summary.counts).map(([id, n]) => (
                  <div key={id} className="flex justify-between text-slate-400">
                    <span>{buildingMap[id]?.name ?? id}</span>
                    <span className="tabular-nums">×{n}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Build cost">
            {Object.keys(summary.cost).length === 0 ? (
              <p className="text-sm text-slate-500">No costed buildings placed.</p>
            ) : (
              <div className="space-y-1 text-xs">
                {Object.entries(summary.cost).map(([item, qty]) => (
                  <div key={item} className="flex justify-between text-slate-400">
                    <span>{item}</span>
                    <span className="tabular-nums text-slate-200">{qty}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {plan && (
            <Card title="Versions">
              <ul className="space-y-1 text-xs">
                {(versions ?? [])
                  .slice()
                  .reverse()
                  .map((v) => (
                    <li key={v.version} className="flex items-center justify-between gap-2">
                      <span className="truncate text-slate-400">
                        v{v.version}
                        {v.comment ? ` · ${v.comment}` : ''}
                      </span>
                      {v.version !== plan.version && (
                        <button className="btn shrink-0" onClick={() => revert(v.version)}>
                          Revert
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
            </Card>
          )}
        </div>
      </div>

      {showHelp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setShowHelp(false)}
        >
          <div
            className="w-80 rounded-lg border border-surface-border bg-surface-raised p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-300">
              Keyboard shortcuts
            </h2>
            <dl className="space-y-2 text-sm text-slate-400">
              {[
                ['Click building, then grid', 'Place'],
                ['Drag a building', 'Move'],
                ['R', 'Rotate selected'],
                ['Delete / Backspace', 'Remove selected'],
                ['Esc', 'Clear selection / tool'],
                ['?', 'Toggle this help'],
              ].map(([keys, action]) => (
                <div key={keys} className="flex justify-between gap-3">
                  <dt className="font-mono text-xs text-slate-300">{keys}</dt>
                  <dd className="text-right">{action}</dd>
                </div>
              ))}
            </dl>
            <button className="btn mt-4 w-full" onClick={() => setShowHelp(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
