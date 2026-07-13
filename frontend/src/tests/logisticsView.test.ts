import { describe, expect, it } from 'vitest';
import type { LogisticsNode } from '../types/logistics';
import { makeProjector, routeWidth, utilizationColor } from '../utils/logisticsView';

const node = (id: string, x: number, y: number): LogisticsNode => ({
  id,
  name: id,
  type: 'factory',
  position: { x, y, z: 0 },
});

describe('utilizationColor', () => {
  it('escalates with load', () => {
    const low = utilizationColor(0.3);
    const busy = utilizationColor(0.7);
    const hot = utilizationColor(0.9);
    const over = utilizationColor(1.2);
    expect(new Set([low, busy, hot, over]).size).toBe(4); // four distinct bands
    expect(over).not.toBe(hot);
  });

  it('flags over-capacity above 1', () => {
    expect(utilizationColor(1.01)).toBe(utilizationColor(5));
  });
});

describe('makeProjector', () => {
  const view = { width: 200, height: 100, padding: 10 };

  it('keeps projected points within the padded viewport', () => {
    const nodes = [node('a', -70000, 149000), node('b', 5000, -88000), node('c', 152000, 90000)];
    const project = makeProjector(nodes, view);
    for (const n of nodes) {
      const p = project(n.position);
      expect(p.x).toBeGreaterThanOrEqual(view.padding - 0.001);
      expect(p.x).toBeLessThanOrEqual(view.width - view.padding + 0.001);
      expect(p.y).toBeGreaterThanOrEqual(view.padding - 0.001);
      expect(p.y).toBeLessThanOrEqual(view.height - view.padding + 0.001);
    }
  });

  it('handles a degenerate single-point network', () => {
    const project = makeProjector([node('a', 100, 100)], view);
    const p = project({ x: 100, y: 100 });
    expect(Number.isFinite(p.x)).toBe(true);
    expect(Number.isFinite(p.y)).toBe(true);
  });
});

describe('routeWidth', () => {
  it('scales with throughput and clamps', () => {
    expect(routeWidth(0)).toBe(1.5);
    expect(routeWidth(600)).toBeCloseTo(5, 5);
    expect(routeWidth(100000)).toBe(8);
  });
});
