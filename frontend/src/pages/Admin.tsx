import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '../components/Card';
import { CheatControl } from '../components/admin/CheatControl';
import { UsersPanel } from '../components/admin/UsersPanel';
import { NoAccess } from '../components/RouteGuards';
import { api } from '../api/endpoints';
import { ApiError } from '../api/http';
import {
  useAdminCatalog,
  useAdminLog,
  useAdminState,
  useBridgeActions,
  useExecuteCheat,
} from '../hooks/useAdmin';
import { useAuth } from '../hooks/useAuth';
import type { CheatCategory } from '../types/admin';

function CategoryPanel({
  category,
  toggles,
  players,
  pending,
  supported,
  onExecute,
}: {
  category: CheatCategory;
  toggles: Record<string, boolean>;
  players: string[];
  pending: boolean;
  /** Set of action ids the bridge implements; null = don't disable anything. */
  supported: Set<string> | null;
  onExecute: (actionId: string, params: Record<string, unknown>) => void;
}) {
  return (
    <div className="space-y-4">
      {category.sections.map((section) => (
        <Card key={section.id} title={section.label}>
          <div className="grid gap-2 lg:grid-cols-2">
            {section.actions.map((action) => (
              <CheatControl
                key={action.id}
                action={action}
                enabled={toggles[action.id] ?? false}
                players={players}
                pending={pending}
                unsupported={supported ? !supported.has(action.id) : false}
                onExecute={onExecute}
              />
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

function AuditLogCard() {
  const { data: log } = useAdminLog();
  return (
    <Card title="Command log">
      {!log?.length ? (
        <p className="text-sm text-slate-500">No commands executed yet.</p>
      ) : (
        <ul className="max-h-64 space-y-1 overflow-y-auto font-mono text-xs">
          {log.map((entry, index) => (
            <li key={index} className="flex flex-wrap gap-2 text-slate-400">
              <span className="text-slate-500">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
              <span className="text-slate-300">{entry.username}</span>
              <span className="text-accent">{entry.action_id}</span>
              <span className={entry.status === 'failed' ? 'text-status-error' : ''}>
                {entry.status}
              </span>
              {Object.keys(entry.params).length > 0 && (
                <span className="text-slate-500">{JSON.stringify(entry.params)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function CheatsPanel() {
  const { data: catalog } = useAdminCatalog();
  const { data: state } = useAdminState();
  const { data: bridge } = useBridgeActions();
  const execute = useExecuteCheat();
  const [activeId, setActiveId] = useState<string | null>(null);
  // Online players for the per-cheat target selector.
  const { data: world } = useQuery({
    queryKey: ['world', 'snapshot'],
    queryFn: api.world.snapshot,
    refetchInterval: 15_000,
  });

  const playerNames = useMemo(
    () => (world?.players ?? []).filter((p) => p.online).map((p) => p.name).sort(),
    [world],
  );
  // Which actions the connected bridge implements (null = disable nothing).
  const supportedSet = useMemo(
    () => (bridge?.supported ? new Set(bridge.supported) : null),
    [bridge],
  );
  if (!catalog) {
    return <p className="text-sm text-slate-500">Loading catalog…</p>;
  }

  const active =
    catalog.categories.find((category) => category.id === activeId) ?? catalog.categories[0];

  return (
    <div className="space-y-4">
      <div
        className={`rounded-md border px-3 py-2 text-sm ${
          catalog.executor === 'command_endpoint'
            ? 'border-status-ok/40 text-status-ok'
            : 'border-status-warn/40 text-status-warn'
        }`}
      >
        {catalog.executor_hint}
      </div>

      {execute.data && (
        <div className="rounded-md border border-surface-border px-3 py-2 text-sm text-slate-300">
          {execute.data.detail}
        </div>
      )}
      {execute.isError && (
        <div className="rounded-md border border-status-error/40 px-3 py-2 text-sm text-status-error">
          {execute.error instanceof ApiError ? execute.error.message : 'Command failed.'}
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {catalog.categories.map((category) => (
          <button
            key={category.id}
            type="button"
            onClick={() => setActiveId(category.id)}
            className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
              category.id === active.id
                ? 'bg-accent/10 font-medium text-accent'
                : 'text-slate-400 hover:bg-surface-overlay hover:text-slate-200'
            }`}
          >
            <span aria-hidden className="mr-1">
              {category.icon}
            </span>
            {category.label}
          </button>
        ))}
      </div>

      <CategoryPanel
        category={active}
        toggles={state?.toggles ?? {}}
        players={playerNames}
        pending={execute.isPending}
        supported={supportedSet}
        onExecute={(actionId, params) => execute.mutate({ actionId, params })}
      />

      <p className="text-xs text-slate-500">
        Achievement-safe: the bridge executes cheats directly (cheat manager / engine calls)
        and never enables Advanced Game Settings or creative mode, which is what disables
        achievements. Cheats that would require AGS are refused by the bridge.
      </p>

      <AuditLogCard />
    </div>
  );
}

type Tab = 'cheats' | 'users';

/** Admin page: cheat panel and account management, each gated by permission. */
export default function Admin() {
  const { hasPermission } = useAuth();
  const canCheat = hasPermission('use:admin-cheats');
  const canManageUsers = hasPermission('manage:users');

  const tabs = useMemo(() => {
    const list: { id: Tab; label: string }[] = [];
    if (canCheat) list.push({ id: 'cheats', label: 'Cheats' });
    if (canManageUsers) list.push({ id: 'users', label: 'Accounts' });
    return list;
  }, [canCheat, canManageUsers]);

  const [tab, setTab] = useState<Tab | null>(null);
  const active = tab ?? tabs[0]?.id ?? null;

  if (tabs.length === 0) return <NoAccess />;

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Admin</h1>
      <div className="inline-flex rounded-lg border border-surface-border bg-surface-raised p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-md px-5 py-2 text-sm font-medium transition-colors ${
              t.id === active
                ? 'bg-accent text-white'
                : 'text-slate-300 hover:bg-surface-overlay'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {active === 'cheats' && <CheatsPanel />}
      {active === 'users' && <UsersPanel />}
    </div>
  );
}
