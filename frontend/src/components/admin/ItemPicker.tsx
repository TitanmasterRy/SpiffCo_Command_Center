import { useEffect, useMemo, useRef, useState } from 'react';
import { useItemCatalog } from '../../hooks/useAdmin';
import type { SpawnItemInfo } from '../../types/admin';

/** Which slice of the catalogue a picker offers, driven by the param it fills. */
export type ItemRestrict = 'item' | 'fluid' | 'gear';

interface ItemPickerProps {
  /** Currently selected item class name (`Desc_IronPlate_C`), or ''. */
  value: string;
  /** Called with the chosen item's class name. */
  onChange: (className: string) => void;
  /**
   * Context filter: ``fluid`` shows only fluids (for piping), ``gear`` only
   * equipment, ``item`` the giveable inventory items (excludes fluids — you
   * can't hold them). Defaults to ``item``.
   */
  restrict?: ItemRestrict;
}

const FIELD =
  'w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-100';

const RESTRICT_NOUN: Record<ItemRestrict, string> = {
  item: 'items',
  fluid: 'fluids',
  gear: 'gear',
};

/**
 * Searchable catalogue of in-game items. Displays friendly names, grouped by
 * category; emits the game class name so the bridge can spawn it. The set it
 * offers is scoped by ``restrict`` to what the target param can actually accept.
 */
export function ItemPicker({ value, onChange, restrict = 'item' }: ItemPickerProps) {
  const { data: allItems = [], isLoading, isError } = useItemCatalog();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  // Scope the catalogue to what this param accepts before searching.
  const items = useMemo(() => {
    if (restrict === 'fluid') return allItems.filter((item) => item.form !== 'solid');
    if (restrict === 'gear') return allItems.filter((item) => item.category === 'Equipment');
    return allItems.filter((item) => item.form === 'solid');
  }, [allItems, restrict]);

  const selected = useMemo(
    () => allItems.find((item) => item.class_name === value),
    [allItems, value],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.class_name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q),
    );
  }, [items, query]);

  // Group filtered results by category, preserving the catalogue's order.
  const groups = useMemo(() => {
    const byCategory = new Map<string, SpawnItemInfo[]>();
    for (const item of filtered) {
      const list = byCategory.get(item.category) ?? [];
      list.push(item);
      byCategory.set(item.category, list);
    }
    return [...byCategory.entries()];
  }, [filtered]);

  // Close on outside click while open.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  const choose = (item: SpawnItemInfo) => {
    onChange(item.class_name);
    setOpen(false);
    setQuery('');
  };

  const buttonLabel = selected
    ? selected.name
    : isLoading
      ? 'Loading items…'
      : isError
        ? 'Item catalogue unavailable'
        : 'Select an item…';

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`${FIELD} flex items-center justify-between text-left`}
      >
        <span className={selected ? 'truncate text-slate-100' : 'truncate text-slate-500'}>
          {buttonLabel}
        </span>
        <span aria-hidden className="ml-2 shrink-0 text-slate-500">
          ▾
        </span>
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-surface-border bg-surface-overlay shadow-lg">
          <input
            autoFocus
            type="text"
            placeholder={`Search ${RESTRICT_NOUN[restrict]}…`}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') setOpen(false);
              if (event.key === 'Enter' && filtered[0]) {
                event.preventDefault();
                choose(filtered[0]);
              }
            }}
            className="w-full border-b border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-100 focus:outline-none"
          />
          <div className="max-h-64 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="px-2 py-2 text-xs text-slate-500">No items match “{query}”.</p>
            ) : (
              groups.map(([category, list]) => (
                <div key={category}>
                  <div className="sticky top-0 bg-surface-overlay px-2 py-1 text-[10px] uppercase tracking-wider text-slate-500">
                    {category} · {list.length}
                  </div>
                  {list.map((item) => (
                    <button
                      key={item.class_name}
                      type="button"
                      onClick={() => choose(item)}
                      title={item.class_name}
                      className={`flex w-full items-center justify-between gap-2 px-2 py-1 text-left text-sm hover:bg-accent/10 ${
                        item.class_name === value ? 'bg-accent/10 text-accent' : 'text-slate-200'
                      }`}
                    >
                      <span className="truncate">{item.name}</span>
                      <span className="shrink-0 font-mono text-[10px] text-slate-500">
                        {item.form === 'solid' ? `×${item.stack_size}` : item.form}
                      </span>
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
          <div className="border-t border-surface-border px-2 py-1 text-[10px] text-slate-500">
            {items.length} {RESTRICT_NOUN[restrict]}
          </div>
        </div>
      )}
    </div>
  );
}
