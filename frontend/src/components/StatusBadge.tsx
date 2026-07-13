export type StatusKind = 'ok' | 'warn' | 'error' | 'idle';

const STYLES: Record<StatusKind, string> = {
  ok: 'bg-status-ok/15 text-status-ok',
  warn: 'bg-status-warn/15 text-status-warn',
  error: 'bg-status-error/15 text-status-error',
  idle: 'bg-status-idle/15 text-status-idle',
};

interface StatusBadgeProps {
  kind: StatusKind;
  label: string;
}

/** Small colored pill for statuses (connection, machine state, alerts). */
export function StatusBadge({ kind, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[kind]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {label}
    </span>
  );
}
