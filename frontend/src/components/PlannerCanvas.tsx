import { useCallback, useMemo, useRef } from 'react';
import type { BuildingInfo, Layout, Placement } from '../types/planner';
import { pixelToCell, placementRect } from '../utils/plannerGrid';

/** Categorical color per building category (validated dark palette). */
const CATEGORY_COLOR: Record<string, string> = {
  production: '#3987e5',
  extraction: '#199e70',
};
const DEFAULT_COLOR = '#9085e9';
const INVALID_COLOR = '#e66767';

const CELL_PX = 16;

interface PlannerCanvasProps {
  layout: Layout;
  buildings: Record<string, BuildingInfo>;
  invalidIds: Set<string>;
  selectedId: string | null;
  /** Building id armed for placement, or null when the pointer only selects. */
  tool: string | null;
  onPlace: (x: number, y: number) => void;
  onSelect: (id: string | null) => void;
  onMove: (id: string, x: number, y: number) => void;
}

interface DragState {
  id: string;
  /** Offset (in cells) from the placement's top-left to the grabbed point. */
  dx: number;
  dy: number;
}

/**
 * SVG grid editor: renders the grid and placements, supports click-to-place,
 * click-to-select, and drag-to-move (snapped to cells). Purely controlled —
 * all state lives in the parent page.
 */
export function PlannerCanvas({
  layout,
  buildings,
  invalidIds,
  selectedId,
  tool,
  onPlace,
  onSelect,
  onMove,
}: PlannerCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<DragState | null>(null);
  const { grid, placements } = layout;
  const w = grid.width * CELL_PX;
  const h = grid.length * CELL_PX;

  const cellAt = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } => {
      const box = svgRef.current!.getBoundingClientRect();
      return {
        x: pixelToCell(clientX - box.left, CELL_PX, grid.width),
        y: pixelToCell(clientY - box.top, CELL_PX, grid.length),
      };
    },
    [grid.width, grid.length],
  );

  const handleBackgroundClick = (event: React.MouseEvent<SVGRectElement>) => {
    if (tool) {
      const { x, y } = cellAt(event.clientX, event.clientY);
      onPlace(x, y);
    } else {
      onSelect(null);
    }
  };

  const startDrag = (event: React.PointerEvent<SVGGElement>, placement: Placement) => {
    event.stopPropagation();
    onSelect(placement.id);
    const { x, y } = cellAt(event.clientX, event.clientY);
    drag.current = { id: placement.id, dx: x - placement.x, dy: y - placement.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<SVGGElement>) => {
    if (!drag.current) return;
    const { x, y } = cellAt(event.clientX, event.clientY);
    onMove(drag.current.id, Math.max(0, x - drag.current.dx), Math.max(0, y - drag.current.dy));
  };

  const endDrag = (event: React.PointerEvent<SVGGElement>) => {
    if (drag.current) {
      event.currentTarget.releasePointerCapture(event.pointerId);
      drag.current = null;
    }
  };

  const gridLines = useMemo(() => {
    const lines: React.ReactNode[] = [];
    for (let i = 0; i <= grid.width; i += 1) {
      lines.push(<line key={`v${i}`} x1={i * CELL_PX} y1={0} x2={i * CELL_PX} y2={h} />);
    }
    for (let j = 0; j <= grid.length; j += 1) {
      lines.push(<line key={`h${j}`} x1={0} y1={j * CELL_PX} x2={w} y2={j * CELL_PX} />);
    }
    return lines;
  }, [grid.width, grid.length, w, h]);

  return (
    <div className="overflow-auto rounded-md border border-surface-border bg-surface p-2">
      <svg
        ref={svgRef}
        width={w}
        height={h}
        className={tool ? 'cursor-copy' : 'cursor-default'}
        role="img"
        aria-label="Factory layout grid"
      >
        <rect x={0} y={0} width={w} height={h} fill="#0f1216" onClick={handleBackgroundClick} />
        <g stroke="#252a33" strokeWidth={1}>
          {gridLines}
        </g>
        {placements.map((placement) => {
          const building = buildings[placement.building];
          if (!building) return null;
          const rect = placementRect(placement, building.footprint, grid.cell_cm);
          const invalid = invalidIds.has(placement.id);
          const selected = placement.id === selectedId;
          const color = invalid ? INVALID_COLOR : CATEGORY_COLOR[building.category] ?? DEFAULT_COLOR;
          return (
            <g
              key={placement.id}
              transform={`translate(${rect.x * CELL_PX}, ${rect.y * CELL_PX})`}
              className="cursor-move"
              onPointerDown={(e) => startDrag(e, placement)}
              onPointerMove={onPointerMove}
              onPointerUp={endDrag}
            >
              <rect
                width={rect.width * CELL_PX}
                height={rect.length * CELL_PX}
                rx={2}
                fill={color}
                fillOpacity={invalid ? 0.5 : 0.75}
                stroke={selected ? '#ffffff' : color}
                strokeWidth={selected ? 2 : 1}
              />
              <title>
                {building.name}
                {placement.clock !== 1 ? ` @ ${Math.round(placement.clock * 100)}%` : ''}
                {invalid ? ' — invalid placement' : ''}
              </title>
              {rect.width >= 3 && rect.length >= 2 && (
                <text
                  x={(rect.width * CELL_PX) / 2}
                  y={(rect.length * CELL_PX) / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={9}
                  fill="#0f1216"
                  fontWeight={600}
                  pointerEvents="none"
                >
                  {building.name.slice(0, Math.max(3, rect.width))}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
