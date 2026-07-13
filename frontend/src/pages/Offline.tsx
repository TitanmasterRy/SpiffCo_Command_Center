import { useRef, useState } from 'react';
import { Card } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { StatusBadge, type StatusKind } from '../components/StatusBadge';
import { ApiError } from '../api/http';
import { useClearSave, useOfflineStatus, useUploadSave } from '../hooks/useOffline';
import type { DataSource, SaveSummary } from '../types/offline';
import { formatDuration, formatMegawatts } from '../utils/format';

const SOURCE_LABEL: Record<DataSource, string> = {
  simulation: 'Simulation',
  frm: 'FRM (live game)',
  save: 'Save file',
};

const CATEGORY_LABEL: Record<string, string> = {
  production: 'Production',
  extraction: 'Extraction',
  generator: 'Generator',
  power_storage: 'Power storage',
  logistics: 'Logistics',
};

function sourceBadge(source: DataSource): { kind: StatusKind; label: string } {
  if (source === 'save') return { kind: 'ok', label: 'Save file' };
  if (source === 'frm') return { kind: 'ok', label: 'FRM (live)' };
  return { kind: 'idle', label: 'Simulation' };
}

/** Offline mode (Phase 12): load a Satisfactory `.sav` as the live data source. */
export default function Offline() {
  const { data: status } = useOfflineStatus();
  const upload = useUploadSave();
  const clear = useClearSave();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const source = status?.source ?? 'simulation';
  const badge = sourceBadge(source);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync(file);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed');
    } finally {
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Offline Mode</h1>
        <StatusBadge kind={badge.kind} label={`Source: ${badge.label}`} />
      </div>

      <Card title="Load a save file">
        <p className="mb-3 text-sm text-slate-400">
          Upload a Satisfactory <code className="font-mono text-xs">.sav</code> file to plan
          and analyze your factory with no live game running. The Dashboard, Power, and
          Advisor pages switch to the save&apos;s data. Building counts and power are read
          from the save; per-machine positions and live rates are not (see notes below).
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept=".sav"
            className="hidden"
            onChange={(e) => void onFile(e.target.files?.[0])}
          />
          <button
            className="btn"
            disabled={upload.isPending}
            onClick={() => inputRef.current?.click()}
          >
            {upload.isPending ? 'Parsing…' : 'Choose .sav file'}
          </button>
          {status?.active && (
            <button
              className="btn"
              disabled={clear.isPending}
              onClick={() => void clear.mutateAsync()}
            >
              {clear.isPending ? 'Restoring…' : `Return to ${SOURCE_LABEL[source === 'save' ? 'simulation' : source]}`}
            </button>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-status-error">{error}</p>}
      </Card>

      {status?.save ? (
        <SaveDetails save={status.save} />
      ) : (
        <Card title="No save loaded">
          <p className="text-sm text-slate-500">
            Currently running on <strong>{SOURCE_LABEL[source]}</strong> data. Load a save
            file above to switch the app to offline analysis.
          </p>
        </Card>
      )}
    </div>
  );
}

function SaveDetails({ save }: { save: SaveSummary }) {
  return (
    <div className="space-y-4">
      <Card title={`Session: ${save.session_name}`}>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
          <Field label="Map" value={save.map_name} />
          <Field label="Build version" value={String(save.build_version)} />
          <Field label="Play time" value={formatDuration(save.play_duration_seconds)} />
          <Field
            label="Saved"
            value={save.saved_at ? new Date(save.saved_at).toLocaleString() : '—'}
          />
        </dl>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard title="Machines" value={save.machine_count.toLocaleString()} detail="Production + extraction" />
        <StatCard title="Generators" value={save.generator_count.toLocaleString()} />
        <StatCard
          title="Est. capacity"
          value={formatMegawatts(save.estimated_power_capacity_mw)}
          detail="Nominal generator output"
        />
        <StatCard
          title="Est. draw"
          value={formatMegawatts(save.estimated_power_consumption_mw)}
          detail="At 100% clock"
        />
      </div>

      <Card title={`Buildings (${save.total_buildings.toLocaleString()} catalogued)`}>
        {save.buildings.length === 0 ? (
          <p className="text-sm text-slate-500">
            No catalogued buildings were identified in this save.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="pb-2 pr-4 font-medium">Building</th>
                  <th className="pb-2 pr-4 font-medium">Category</th>
                  <th className="pb-2 pr-4 text-right font-medium">Count</th>
                  <th className="pb-2 text-right font-medium">Power (each)</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {save.buildings.map((b) => (
                  <tr key={b.class_name} className="border-t border-surface-border">
                    <td className="py-1.5 pr-4 text-slate-200">{b.name}</td>
                    <td className="py-1.5 pr-4 text-slate-400">
                      {CATEGORY_LABEL[b.category] ?? b.category}
                    </td>
                    <td className="py-1.5 pr-4 text-right text-slate-200">{b.count}</td>
                    <td className="py-1.5 text-right text-slate-400">
                      {b.power_mw > 0 ? formatMegawatts(b.power_mw) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="text-xs text-slate-600">
        Power figures are estimates from nominal building power at 100% clock. The World Map
        and Logistics pages are not populated from saves (positions are not extracted).
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-slate-500">{label}:</dt>
      <dd className="text-slate-200">{value}</dd>
    </div>
  );
}
