import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useAppInfo, useHealth } from '../hooks/useHealth';
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
export function TopBar() {
  const wsStatus = useConnectionStore((state) => state.wsStatus);
  const { data: health } = useHealth();
  const { data: info } = useAppInfo();
  const { data: offline } = useOfflineStatus();

  const ws = wsBadge(wsStatus);
  const frm = frmBadge(health?.frm);
  const source = sourceBadge(offline?.source);

  return (
    <header className="flex h-14 items-center justify-between border-b border-surface-border bg-surface-raised px-6">
      <div className="flex items-center gap-3">
        <StatusBadge kind={ws.kind} label={ws.label} />
        <StatusBadge kind={frm.kind} label={frm.label} />
        <StatusBadge kind={source.kind} label={source.label} />
      </div>
      <div className="text-xs text-slate-500">
        {info ? `v${info.version} · ${info.environment}` : '…'}
      </div>
    </header>
  );
}
