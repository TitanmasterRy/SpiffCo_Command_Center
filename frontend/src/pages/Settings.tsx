import { Card } from '../components/Card';
import { useAppInfo } from '../hooks/useHealth';

/** Settings page: app info now; preferences and FRM configuration later. */
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
      <Card title="FRM connection">
        <p className="text-sm text-slate-400">
          Configure the Ficsit Remote Monitoring endpoint via environment variables for
          now (<code className="font-mono text-xs">SPIFFCO_FRM_BASE_URL</code>). In-app
          configuration arrives with Phase 11.
        </p>
      </Card>
    </div>
  );
}
