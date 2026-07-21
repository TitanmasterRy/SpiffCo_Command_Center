import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useAppInfo, useHealth } from '../hooks/useHealth';
import { useAuth, useLogout } from '../hooks/useAuth';
import { useOfflineStatus } from '../hooks/useOffline';
import { useConnectionStore } from '../stores/connectionStore';
import type { DataSource } from '../types/offline';

function wsBadge(status: string): { kind: StatusKind; label: string } {
  if (status === 'open') return { kind: 'ok', label: 'Live' };
  if (status === 'connecting') return { kind: 'warn', label: 'Connecting' };
  return { kind: 'error', label: 'Offline' };
}

function frmBadge(frm?: string): { kind: StatusKind; label: string } {
  if (frm === 'connected') return { kind: 'ok', label: 'FRM connected' };
  if (frm === 'disconnected') return { kind: 'error', label: 'FRM disconnected' };
  return { kind: 'idle', label: 'FRM not configured' };
}

function sourceBadge(source?: DataSource): { kind: StatusKind; label: string } {
  if (source === 'save') return { kind: 'ok', label: 'Save file' };
  if (source === 'frm') return { kind: 'ok', label: 'Live game' };
  return { kind: 'idle', label: 'Simulation' };
}

/** Top bar showing global connection health and app version. */
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const wsStatus = useConnectionStore((state) => state.wsStatus);
  const { data: health } = useHealth();
  const { data: info } = useAppInfo();
  const { data: offline } = useOfflineStatus();

  const ws = wsBadge(wsStatus);
  const frm = frmBadge(health?.frm);
  const source = sourceBadge(offline?.source);

  return (
    <header className="flex h-14 items-center justify-between gap-2 border-b border-surface-border bg-surface-raised px-3 md:px-6">
      <div className="flex min-w-0 items-center gap-2 md:gap-3">
        <button
          onClick={onMenu}
          aria-label="Open navigation menu"
          className="-ml-1 rounded-md p-2 text-lg leading-none text-slate-300 hover:bg-surface-overlay md:hidden"
        >
          ☰
        </button>
        <div className="flex min-w-0 items-center gap-2 overflow-x-auto md:gap-3">
          <StatusBadge kind={ws.kind} label={ws.label} />
          <StatusBadge kind={frm.kind} label={frm.label} />
          <StatusBadge kind={source.kind} label={source.label} />
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden text-xs text-slate-500 sm:block">
          {info ? `v${info.version} · ${info.environment}` : '…'}
        </span>
        <UserMenu />
      </div>
    </header>
  );
}

/** Current user + sign-out, shown only when authentication is enabled. */
function UserMenu() {
  const { enabled, username } = useAuth();
  const logout = useLogout();
  if (!enabled || !username) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-xs text-slate-400 sm:inline">
        <span className="text-slate-200">{username}</span>
      </span>
      <button
        type="button"
        onClick={logout}
        className="rounded-md border border-surface-border px-2.5 py-1 text-xs text-slate-300 hover:bg-surface-overlay"
      >
        Sign out
      </button>
    </div>
  );
}
