import { useState } from 'react';
import type { CheatAction, CheatParam } from '../../types/admin';
import { ItemPicker } from './ItemPicker';

interface CheatControlProps {
  action: CheatAction;
  /** Current server-side value for toggle controls. */
  enabled: boolean;
  /** Online player names for player-scoped actions. */
  players: string[];
  pending: boolean;
  /** True when the connected bridge doesn't implement this action yet. */
  unsupported?: boolean;
  onExecute: (actionId: string, params: Record<string, unknown>) => void;
}

function initialValues(params: CheatParam[]): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const p of params) {
    if (p.default !== null && p.default !== undefined) values[p.name] = p.default;
  }
  return values;
}

interface ParamInputProps {
  param: CheatParam;
  value: unknown;
  onChange: (value: unknown) => void;
}

function ParamInput({ param, value, onChange }: ParamInputProps) {
  const inputClass =
    'w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-100';

  if (param.type === 'item') {
    // The param name signals which slice of the catalogue is valid here.
    const restrict = param.name === 'fluid' ? 'fluid' : param.name === 'gear' ? 'gear' : 'item';
    return <ItemPicker value={String(value ?? '')} onChange={onChange} restrict={restrict} />;
  }

  if (param.type === 'select') {
    return (
      <select
        value={String(value ?? param.options?.[0] ?? '')}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      >
        {(param.options ?? []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (param.type === 'slider') {
    const current = Number(value ?? param.default ?? param.min ?? 0);
    return (
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={param.min ?? 0}
          max={param.max ?? 100}
          step={param.step ?? 1}
          value={current}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 accent-accent"
        />
        <span className="w-16 shrink-0 text-right font-mono text-xs text-slate-300">
          {current}
          {param.unit ?? ''}
        </span>
      </div>
    );
  }

  if (param.type === 'number') {
    return (
      <input
        type="number"
        min={param.min ?? undefined}
        max={param.max ?? undefined}
        step={param.step ?? undefined}
        value={value === undefined || value === null ? '' : Number(value)}
        onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
        className={inputClass}
      />
    );
  }

  if (param.type === 'coords') {
    return (
      <input
        type="text"
        placeholder="x, y, z"
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
        className={`${inputClass} font-mono`}
      />
    );
  }

  // Plain text (free-form) input.
  return (
    <input
      type="text"
      value={String(value ?? '')}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
    />
  );
}

interface PlayerSelectProps {
  players: string[];
  value: string;
  onChange: (name: string) => void;
}

/** Target selector for player-scoped actions; empty value = first player. */
function PlayerSelect({ players, value, onChange }: PlayerSelectProps) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">
        Target player
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-surface-border bg-surface px-2 py-1.5 text-sm text-slate-100"
      >
        <option value="">First player (default)</option>
        {players.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

interface ActionTriggerProps {
  action: CheatAction;
  enabled: boolean;
  disabled: boolean;
  confirming: boolean;
  unsupported: boolean;
  onRun: () => void;
  onCancelConfirm: () => void;
}

/** The right-hand control for one cheat: a switch for toggles, a button otherwise. */
function ActionTrigger({
  action,
  enabled,
  disabled,
  confirming,
  unsupported,
  onRun,
  onCancelConfirm,
}: ActionTriggerProps) {
  if (action.control === 'toggle') {
    return (
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        disabled={disabled}
        onClick={onRun}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
          enabled ? 'bg-accent' : 'bg-surface-overlay'
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
            enabled ? 'left-[22px]' : 'left-0.5'
          }`}
        />
      </button>
    );
  }
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onRun}
      className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
        confirming
          ? 'bg-status-error text-white'
          : action.danger
            ? 'border border-status-error/60 text-status-error hover:bg-status-error/10'
            : 'bg-accent text-white hover:bg-accent/80'
      }`}
      onBlur={onCancelConfirm}
    >
      {unsupported ? 'N/A' : confirming ? 'Confirm?' : 'Run'}
    </button>
  );
}

/** One cheat rendered from catalog data: its inputs plus a run button or toggle. */
export function CheatControl({
  action,
  enabled,
  players,
  pending,
  unsupported = false,
  onExecute,
}: CheatControlProps) {
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    initialValues(action.params),
  );
  const [targetPlayer, setTargetPlayer] = useState('');
  const [confirming, setConfirming] = useState(false);

  const run = () => {
    if (unsupported) return;
    if (action.danger && !confirming) {
      setConfirming(true);
      return;
    }
    setConfirming(false);
    const params =
      action.scope === 'player' && targetPlayer ? { ...values, player: targetPlayer } : values;
    onExecute(action.id, params);
  };

  return (
    <div
      className={`rounded-md border border-surface-border bg-surface p-3 ${
        unsupported ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm text-slate-200">{action.label}</span>
            {action.affects_all && (
              <span
                className="shrink-0 rounded border border-status-warn/50 px-1 py-px text-[10px] uppercase tracking-wider text-status-warn"
                title="Alters state shared by every player on the server"
              >
                All players
              </span>
            )}
            {unsupported && (
              <span
                className="shrink-0 rounded border border-surface-border px-1 py-px text-[10px] uppercase tracking-wider text-slate-500"
                title="The installed game bridge mod doesn't implement this action yet"
              >
                Unavailable
              </span>
            )}
          </div>
          {unsupported ? (
            <div className="mt-0.5 text-xs text-slate-500">
              Not implemented in the installed bridge mod.
            </div>
          ) : (
            action.hint && <div className="mt-0.5 text-xs text-slate-500">{action.hint}</div>
          )}
        </div>
        <ActionTrigger
          action={action}
          enabled={enabled}
          disabled={pending || unsupported}
          confirming={confirming}
          unsupported={unsupported}
          onRun={run}
          onCancelConfirm={() => setConfirming(false)}
        />
      </div>
      {(action.params.length > 0 || action.scope === 'player') && (
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {action.scope === 'player' && (
            <PlayerSelect players={players} value={targetPlayer} onChange={setTargetPlayer} />
          )}
          {action.params.map((param) => (
            <label key={param.name} className="block">
              <span className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">
                {param.label}
              </span>
              <ParamInput
                param={param}
                value={values[param.name]}
                onChange={(value) => setValues((prev) => ({ ...prev, [param.name]: value }))}
              />
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
