/** Formatting helpers shared across the UI. */

/** Format seconds as `1d 2h 3m` / `4m 5s` for uptime displays. */
export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const rest = seconds % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${rest}s`;
  return `${rest}s`;
}

/** Format a rate as `123.4/min` (items per minute, the game's native unit). */
export function formatPerMinute(value: number): string {
  return `${value.toFixed(1)}/min`;
}

/** Format megawatts with one decimal, e.g. `1,234.5 MW`. */
export function formatMegawatts(value: number): string {
  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} MW`;
}
