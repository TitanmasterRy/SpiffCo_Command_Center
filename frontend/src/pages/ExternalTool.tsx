import { useState } from 'react';

interface ExternalToolProps {
  /** Page heading shown above the embed. */
  title: string;
  /** URL of the external tool to embed. */
  src: string;
  /** Hostname shown as the attribution/source hint. */
  source: string;
  /** Optional note rendered next to the source (e.g. live-feed caveats). */
  note?: string;
}

/**
 * Full-height iframe embed of a third-party community tool.
 *
 * The embedded sites keep their own state (browser storage inside the frame),
 * so plans survive navigation away and back. A reload button remounts the
 * frame for when the embedded app gets into a bad state.
 */
export default function ExternalTool({ title, src, source, note }: ExternalToolProps) {
  // Bumping the key remounts the iframe, forcing a clean reload.
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <h1 className="text-lg font-semibold text-slate-100">{title}</h1>
        <span className="text-xs text-slate-500">
          {source}
          {note ? ` — ${note}` : ''}
        </span>
        <span className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => setReloadKey((k) => k + 1)}
            className="rounded-md border border-surface-border px-2.5 py-1 text-xs text-slate-300 transition-colors hover:bg-surface-overlay"
          >
            ⟳ Reload
          </button>
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border border-surface-border px-2.5 py-1 text-xs text-slate-300 transition-colors hover:bg-surface-overlay"
          >
            ↗ Open in new tab
          </a>
        </span>
      </div>
      <iframe
        key={reloadKey}
        src={src}
        title={title}
        className="min-h-0 w-full flex-1 rounded-lg border border-surface-border bg-white"
        allow="clipboard-read; clipboard-write; fullscreen"
      />
    </div>
  );
}
