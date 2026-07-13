import { useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { ProductionGraph } from '../components/ProductionGraph';
import { StatusBadge } from '../components/StatusBadge';
import { useItems, useProducibleRecipes, useProductionPlan } from '../hooks/useProduction';
import type { ProductionNode, ProductionRequest } from '../types/production';
import { formatMegawatts, formatPerMinute } from '../utils/format';
import { buildProductionGraph } from '../utils/productionGraph';

type ChainView = 'tree' | 'graph' | 'items' | 'buildings';
const CHAIN_VIEWS: { id: ChainView; label: string }[] = [
  { id: 'tree', label: 'Tree list' },
  { id: 'graph', label: 'Network graph' },
  { id: 'items', label: 'Items' },
  { id: 'buildings', label: 'Buildings' },
];

/** Distinct craftable items in a solved tree that have alternate recipes. */
function craftableItems(node: ProductionNode, into: Set<string> = new Set()): Set<string> {
  if (!node.is_raw) into.add(node.item);
  for (const child of node.inputs) craftableItems(child, into);
  return into;
}

interface TreeRowProps {
  node: ProductionNode;
  depth: number;
  somersloop: Set<string>;
  onToggleSloop: (item: string) => void;
}

/** One indented row of the production tree, recursing into its inputs. */
function TreeRow({ node, depth, somersloop, onToggleSloop }: TreeRowProps) {
  return (
    <>
      <div
        className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-surface-border/60 py-1.5 text-sm"
        style={{ paddingLeft: `${depth * 1.25}rem` }}
      >
        <span className={node.is_raw ? 'text-status-idle' : 'text-slate-200'}>
          {node.item_name}
        </span>
        <span className="tabular-nums text-xs text-slate-500">
          {formatPerMinute(node.rate_per_min)}
        </span>
        {node.is_raw ? (
          <StatusBadge kind="idle" label="raw" />
        ) : (
          <>
            <span className="text-xs text-slate-500">
              {node.machine_count.toFixed(2)}× {node.machine_name}
            </span>
            <span className="text-xs text-slate-600">· {node.recipe_name}</span>
            <span className="tabular-nums text-xs text-accent">
              {formatMegawatts(node.power_mw)}
            </span>
            <label className="flex items-center gap-1 text-xs text-slate-500">
              <input
                type="checkbox"
                checked={somersloop.has(node.item)}
                onChange={() => onToggleSloop(node.item)}
              />
              sloop
            </label>
          </>
        )}
      </div>
      {node.inputs.map((child) => (
        <TreeRow
          key={`${child.item}-${depth}`}
          node={child}
          depth={depth + 1}
          somersloop={somersloop}
          onToggleSloop={onToggleSloop}
        />
      ))}
    </>
  );
}

/** Production Planner (Phase 5): target → balanced recipe chain + shopping list. */
export default function Planner() {
  const { data: items } = useItems();
  const producible = useProducibleRecipes();

  const itemOptions = useMemo(
    () =>
      (items ?? [])
        .filter((i) => (producible[i.id]?.length ?? 0) > 0)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [items, producible],
  );
  const nameOf = useMemo(() => {
    const map: Record<string, string> = {};
    for (const i of items ?? []) map[i.id] = i.name;
    return (id: string) => map[id] ?? id;
  }, [items]);

  const [target, setTarget] = useState('');
  const [rate, setRate] = useState(60);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [somersloop, setSomersloop] = useState<Set<string>>(new Set());
  const [chainView, setChainView] = useState<ChainView>('tree');

  const request: ProductionRequest | null = target
    ? { item: target, rate_per_min: rate, recipe_overrides: overrides, somersloop_items: [...somersloop] }
    : null;
  const { data: plan, isFetching, error } = useProductionPlan(request);

  const toggleSloop = (item: string) =>
    setSomersloop((prev) => {
      const next = new Set(prev);
      next.has(item) ? next.delete(item) : next.add(item);
      return next;
    });

  const setOverride = (item: string, recipeId: string) =>
    setOverrides((prev) => {
      const next = { ...prev };
      const isDefault = producible[item]?.[0]?.id === recipeId;
      if (isDefault) delete next[item];
      else next[item] = recipeId;
      return next;
    });

  // Items in the current tree that have more than one recipe to choose from.
  const alternableItems = useMemo(() => {
    if (!plan) return [] as string[];
    return [...craftableItems(plan.root)].filter((item) => (producible[item]?.length ?? 0) > 1);
  }, [plan, producible]);

  const recipeFor = (item: string): string =>
    overrides[item] ?? producible[item]?.[0]?.id ?? '';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-100">Production Planner</h1>
        {isFetching && <StatusBadge kind="idle" label="Solving…" />}
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-widest">Target item</span>
            <select
              value={target}
              onChange={(e) => {
                setTarget(e.target.value);
                setOverrides({});
                setSomersloop(new Set());
              }}
              className="w-56 rounded border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="">Select an item…</option>
              {itemOptions.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-widest">Rate (per min)</span>
            <input
              type="number"
              min={0.1}
              step={10}
              value={rate}
              onChange={(e) => setRate(Math.max(0.1, Number(e.target.value)))}
              className="w-32 rounded border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-200"
            />
          </label>
        </div>

        {alternableItems.length > 0 && (
          <div className="mt-4 border-t border-surface-border pt-3">
            <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">
              Alternate recipes
            </p>
            <div className="flex flex-wrap gap-3">
              {alternableItems.map((item) => (
                <label key={item} className="text-xs text-slate-400">
                  <span className="mb-1 block">{nameOf(item)}</span>
                  <select
                    value={recipeFor(item)}
                    onChange={(e) => setOverride(item, e.target.value)}
                    className="rounded border border-surface-border bg-surface px-2 py-1 text-sm text-slate-200"
                  >
                    {(producible[item] ?? []).map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                        {r.is_alternate ? ' ★' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </div>
        )}
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-status-error">
            Could not solve: {(error as Error).message}
          </p>
        </Card>
      )}

      {plan && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_20rem]">
          <Card title="Production chain">
            <div className="mb-3 flex flex-wrap gap-1.5">
              {CHAIN_VIEWS.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setChainView(v.id)}
                  className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
                    chainView === v.id
                      ? 'border-accent/50 bg-accent/10 text-accent'
                      : 'border-surface-border bg-surface-raised text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>

            {chainView === 'tree' && (
              <div className="min-w-0">
                <TreeRow
                  node={plan.root}
                  depth={0}
                  somersloop={somersloop}
                  onToggleSloop={toggleSloop}
                />
              </div>
            )}
            {chainView === 'graph' && <ProductionGraph root={plan.root} />}
            {chainView === 'items' && (
              <ItemsView root={plan.root} />
            )}
            {chainView === 'buildings' && (
              <BuildingsView counts={plan.totals.machine_counts} />
            )}

            {plan.warnings.length > 0 && (
              <ul className="mt-3 space-y-1 border-t border-surface-border pt-2 text-xs text-status-warn">
                {plan.warnings.map((w) => (
                  <li key={w}>⚠ {w}</li>
                ))}
              </ul>
            )}
          </Card>

          <div className="space-y-4">
            <Card title="Totals">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Total power</dt>
                  <dd className="tabular-nums text-slate-100">
                    {formatMegawatts(plan.totals.power_mw)}
                  </dd>
                </div>
              </dl>
              <div className="mt-3 space-y-1 border-t border-surface-border pt-2 text-xs">
                {Object.entries(plan.totals.machine_counts).map(([id, n]) => (
                  <div key={id} className="flex justify-between text-slate-400">
                    <span>{id}</span>
                    <span className="tabular-nums text-slate-200">{n.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Raw materials / min">
              <ShoppingRows map={plan.totals.raw_materials} nameOf={nameOf} suffix="/min" />
            </Card>

            {Object.keys(plan.totals.byproducts).length > 0 && (
              <Card title="Byproducts / min">
                <ShoppingRows map={plan.totals.byproducts} nameOf={nameOf} suffix="/min" />
              </Card>
            )}

            <Card title="Build cost">
              <ShoppingRows map={plan.totals.build_cost} nameOf={nameOf} />
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

/** Flat per-item view: every distinct item in the tree with its total rate. */
function ItemsView({ root }: { root: ProductionNode }) {
  const nodes = useMemo(
    () => buildProductionGraph(root).nodes.sort((a, b) => b.rate - a.rate),
    [root],
  );
  return (
    <div className="space-y-1 text-sm">
      {nodes.map((n) => (
        <div
          key={n.item}
          className="flex flex-wrap items-center gap-x-3 border-b border-surface-border/60 py-1.5"
        >
          <span className={n.isRaw ? 'text-status-idle' : 'text-slate-200'}>{n.name}</span>
          <span className="tabular-nums text-xs text-slate-500">{formatPerMinute(n.rate)}</span>
          {n.isRaw ? (
            <StatusBadge kind="idle" label="raw" />
          ) : (
            <span className="text-xs text-slate-500">
              {n.machineCount.toFixed(2)}× {n.machineName} · {formatMegawatts(n.powerMw)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

/** Per-building view: total machine count for each building in the plan. */
function BuildingsView({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0)
    return <p className="text-sm text-slate-500">No buildings required.</p>;
  return (
    <div className="space-y-1 text-sm">
      {entries.map(([id, n]) => (
        <div
          key={id}
          className="flex items-center justify-between border-b border-surface-border/60 py-1.5"
        >
          <span className="text-slate-200">{id}</span>
          <span className="tabular-nums text-xs text-slate-400">
            {n.toFixed(2)}× ({Math.ceil(n)} built)
          </span>
        </div>
      ))}
    </div>
  );
}

function ShoppingRows({
  map,
  nameOf,
  suffix = '',
}: {
  map: Record<string, number>;
  nameOf: (id: string) => string;
  suffix?: string;
}) {
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return <p className="text-sm text-slate-500">Nothing required.</p>;
  return (
    <div className="space-y-1 text-xs">
      {entries.map(([item, qty]) => (
        <div key={item} className="flex justify-between text-slate-400">
          <span>{nameOf(item)}</span>
          <span className="tabular-nums text-slate-200">
            {qty % 1 === 0 ? qty : qty.toFixed(2)}
            {suffix}
          </span>
        </div>
      ))}
    </div>
  );
}
