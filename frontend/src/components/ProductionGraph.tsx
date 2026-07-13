import { useMemo, useRef, useState } from 'react';
import {
  buildProductionGraph,
  NODE_H,
  NODE_W,
  type ProductionGraphNode,
} from '../utils/productionGraph';
import type { ProductionNode } from '../types/production';
import { formatMegawatts, formatPerMinute } from '../utils/format';

/**
 * SCIM-style network graph of a production chain. The tree is flattened to a
 * left-to-right layered DAG (final product on the left, raw inputs on the
 * right); drag to pan, scroll to zoom.
 */
export function ProductionGraph({ root }: { root: ProductionNode }) {
  const graph = useMemo(() => buildProductionGraph(root), [root]);
  const [view, setView] = useState({ x: 24, y: 24, scale: 1 });
  const drag = useRef<{ x: number; y: number } | null>(null);

  const byItem = useMemo(() => {
    const m = new Map<string, ProductionGraphNode>();
    for (const n of graph.nodes) m.set(n.item, n);
    return m;
  }, [graph]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    setView((v) => ({ ...v, scale: Math.min(2.5, Math.max(0.2, v.scale * factor)) }));
  };
  const onMouseDown = (e: React.MouseEvent) => {
    drag.current = { x: e.clientX - view.x, y: e.clientY - view.y };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!drag.current) return;
    setView((v) => ({ ...v, x: e.clientX - drag.current!.x, y: e.clientY - drag.current!.y }));
  };
  const endDrag = () => {
    drag.current = null;
  };

  return (
    <div
      className="relative h-[30rem] w-full cursor-grab overflow-hidden rounded-md bg-[#10131a] active:cursor-grabbing"
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={endDrag}
      onMouseLeave={endDrag}
    >
      <svg className="h-full w-full select-none">
        <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
          {graph.edges.map((edge) => {
            const a = byItem.get(edge.from);
            const b = byItem.get(edge.to);
            if (!a || !b) return null;
            const x1 = a.x + NODE_W;
            const y1 = a.y + NODE_H / 2;
            const x2 = b.x;
            const y2 = b.y + NODE_H / 2;
            const mid = (x1 + x2) / 2;
            return (
              <path
                key={`${edge.from} ${edge.to}`}
                d={`M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke="#3987e5"
                strokeOpacity={0.4}
                strokeWidth={1.5}
              />
            );
          })}
          {graph.nodes.map((n) => (
            <g key={n.item} transform={`translate(${n.x} ${n.y})`}>
              <rect
                width={NODE_W}
                height={NODE_H}
                rx={6}
                fill={n.isRaw ? '#1a2230' : '#182135'}
                stroke={n.isRaw ? '#c98500' : '#3987e5'}
                strokeWidth={1.5}
              />
              <text x={10} y={19} fill="#e2e8f0" fontSize={12} fontWeight={600}>
                {truncate(n.name, 20)}
              </text>
              <text x={10} y={35} fill="#94a3b8" fontSize={10}>
                {formatPerMinute(n.rate)}
              </text>
              <text x={10} y={49} fill={n.isRaw ? '#c98500' : '#64748b'} fontSize={10}>
                {n.isRaw
                  ? 'raw'
                  : `${n.machineCount.toFixed(1)}× ${truncate(n.machineName ?? '', 14)} · ${formatMegawatts(n.powerMw)}`}
              </text>
            </g>
          ))}
        </g>
      </svg>
      <button
        onClick={() => setView({ x: 24, y: 24, scale: 1 })}
        className="absolute bottom-2 right-2 rounded-md border border-surface-border bg-surface-raised px-2 py-1 text-xs text-slate-300 hover:text-slate-100"
      >
        Reset view
      </button>
    </div>
  );
}

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}
