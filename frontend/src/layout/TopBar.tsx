import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useAppInfo, useHealth } from '../hooks/useHealth';
import { useConnectionStore } from '../stores/connectionStore';

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

/** Top bar showing global connection health and app version. */
export function TopBar() {
  const wsStatus = useConnectionStore((state) => state.wsStatus);
  const { data: health } = useHealth();
  const { data: info } = useAppInfo();

  const ws = wsBadge(wsStatus);
  const frm = frmBadge(health?.frm);

  return (
    <header className="flex h-14 items-center justify-between border-b border-surface-border bg-surface-raised px-6">
      <div className="flex items-center gap-3">
        <StatusBadge kind={ws.kind} label={ws.label} />
        <StatusBadge kind={frm.kind} label={frm.label} />
      </div>
      <div className="text-xs text-slate-500">
        {info ? `v${info.version} · ${info.environment}` : '…'}
      </div>
    </header>
  );
}
