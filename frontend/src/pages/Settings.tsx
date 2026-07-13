import { useEffect, useState } from 'react';
import { Card } from '../components/Card';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { useAppInfo } from '../hooks/useHealth';
import { useFrmConfig, useTestFrmConfig, useUpdateFrmConfig } from '../hooks/useFrmConfig';
import type { FrmConfigStatus } from '../types/api';
import { ApiError } from '../api/http';

const SOURCE_BADGE: Record<FrmConfigStatus['source'], { kind: StatusKind; label: string }> = {
  frm: { kind: 'ok', label: 'Live game (FRM)' },
  save: { kind: 'idle', label: 'Save file' },
  simulation: { kind: 'idle', label: 'Simulation' },
};

const STATE_BADGE: Record<FrmConfigStatus['state'], { kind: StatusKind; label: string }> = {
  connected: { kind: 'ok', label: 'Connected' },
  connecting: { kind: 'warn', label: 'Connecting' },
  error: { kind: 'error', label: 'Error' },
  disconnected: { kind: 'idle', label: 'Disconnected' },
};

function FrmConnectionCard() {
  const { data: status } = useFrmConfig();
  const update = useUpdateFrmConfig();
  const test = useTestFrmConfig();

  const [enabled, setEnabled] = useState(false);
  const [baseUrl, setBaseUrl] = useState('http://localhost:8080');

  // Seed the form from the server once loaded (and when it changes elsewhere).
  useEffect(() => {
    if (status) {
      setEnabled(status.enabled);
      setBaseUrl(status.base_url);
    }
  }, [status]);

  if (!status) {
    return (
      <Card title="FRM connection">
        <p className="text-sm text-slate-500">Loading…</p>
      </Card>
    );
  }

  const source = SOURCE_BADGE[status.source];
  const state = STATE_BADGE[status.state];
  const dirty = enabled !== status.enabled || baseUrl.trim() !== status.base_url;
  const errorMessage = (err: unknown) =>
    err instanceof ApiError ? err.message : 'Request failed.';

  return (
    <Card title="FRM connection">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Data source:</span>
          <StatusBadge kind={source.kind} label={source.label} />
          {status.enabled && <StatusBadge kind={state.kind} label={state.label} />}
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 rounded border-surface-border bg-surface-raised"
          />
          Connect to live game data via the Ficsit Remote Monitoring mod
        </label>

        <div className="space-y-1">
          <label htmlFor="frm-url" className="block text-xs uppercase tracking-wider text-slate-500">
            FRM endpoint URL
          </label>
          <input
            id="frm-url"
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://your-game-machine:8080"
            disabled={!enabled}
            className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 font-mono text-sm text-slate-100 disabled:opacity-50"
          />
          <p className="text-xs text-slate-500">
            The address where the FRM mod's web server is reachable from this backend.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => update.mutate({ enabled, base_url: baseUrl.trim() })}
            disabled={update.isPending || (!dirty && !update.isError)}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {update.isPending ? 'Applying…' : 'Save & apply'}
          </button>
          <button
            type="button"
            onClick={() => test.mutate({ enabled: true, base_url: baseUrl.trim() })}
            disabled={test.isPending || !baseUrl.trim()}
            className="rounded-md border border-surface-border px-4 py-2 text-sm font-medium text-slate-200 disabled:opacity-50"
          >
            {test.isPending ? 'Testing…' : 'Test connection'}
          </button>
        </div>

        {test.data && (
          <p className={`text-sm ${test.data.reachable ? 'text-status-ok' : 'text-status-warn'}`}>
            {test.data.message}
          </p>
        )}
        {test.isError && <p className="text-sm text-status-error">{errorMessage(test.error)}</p>}

        {update.isError && (
          <p className="text-sm text-status-error">{errorMessage(update.error)}</p>
        )}
        {update.isSuccess && status.message && (
          <p
            className={`text-sm ${
              status.source === 'frm' ? 'text-status-ok' : 'text-status-warn'
            }`}
          >
            {status.message}
          </p>
        )}

        <p className="text-xs text-slate-500">
          Settings persist across restarts. The environment variables{' '}
          <code className="font-mono">SPIFFCO_FRM_ENABLED</code> /{' '}
          <code className="font-mono">SPIFFCO_FRM_BASE_URL</code> set the initial default.
        </p>
      </div>
    </Card>
  );
}

/** Settings page: app info and live FRM connection configuration. */
export default function Settings() {
  const { data: info } = useAppInfo();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-100">Settings</h1>
      <Card title="Application">
        {info ? (
          <dl className="space-y-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-slate-500">Name:</dt>
              <dd>{info.name}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">Version:</dt>
              <dd>{info.version}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">Environment:</dt>
              <dd>{info.environment}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-slate-500">Loading…</p>
        )}
      </Card>
      <FrmConnectionCard />
    </div>
  );
}
