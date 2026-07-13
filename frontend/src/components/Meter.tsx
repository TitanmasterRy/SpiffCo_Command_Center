interface MeterProps {
  label: string;
  value: number;
  max: number;
  /** Formatted value text, e.g. "412.3/480 /min". */
  display: string;
}

/** Horizontal meter: single-hue fill on a muted track with a right-aligned value. */
export function Meter({ label, value, max, display }: MeterProps) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="text-xs tabular-nums text-slate-400">{display}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-overlay">
        <div
          className="h-full rounded-full bg-[#3987e5]"
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemax={max}
          aria-label={label}
        />
      </div>
    </div>
  );
}
