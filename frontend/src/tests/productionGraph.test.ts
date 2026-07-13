import { describe, expect, it } from 'vitest';
import type { ProductionNode } from '../types/production';
import { buildProductionGraph } from '../utils/productionGraph';

/** Minimal node factory for building test trees. */
function node(item: string, rate: number, inputs: ProductionNode[] = [], isRaw = false): ProductionNode {
  return {
    item,
    item_name: item,
    rate_per_min: rate,
    is_raw: isRaw,
    recipe_id: isRaw ? null : `${item}-recipe`,
    recipe_name: isRaw ? null : `${item} recipe`,
    machine: isRaw ? null : 'smelter',
    machine_name: isRaw ? null : 'Smelter',
    machine_count: isRaw ? 0 : rate / 30,
    power_mw: isRaw ? 0 : rate,
    somersloop: false,
    byproducts: [],
    inputs,
  };
}

describe('buildProductionGraph', () => {
  it('lays out a simple chain left-to-right by longest path', () => {
    const tree = node('plate', 20, [node('ingot', 30, [node('ore', 30, [], true)])]);
    const g = buildProductionGraph(tree);
    const level = (item: string) => g.nodes.find((n) => n.item === item)!.level;
    expect(level('plate')).toBe(0);
    expect(level('ingot')).toBe(1);
    expect(level('ore')).toBe(2);
    expect(g.edges).toContainEqual({ from: 'plate', to: 'ingot', rate: 30 });
  });

  it('merges an item used by two branches into one node with summed rate', () => {
    // ingot feeds both a plate branch and a rod branch.
    const tree = node('assembly', 10, [
      node('plate', 20, [node('ingot', 30, [node('ore', 30, [], true)])]),
      node('rod', 15, [node('ingot', 15, [node('ore', 15, [], true)])]),
    ]);
    const g = buildProductionGraph(tree);
    const ingots = g.nodes.filter((n) => n.item === 'ingot');
    expect(ingots).toHaveLength(1);
    expect(ingots[0].rate).toBe(45); // 30 + 15
    // ore appears twice too and must merge.
    expect(g.nodes.filter((n) => n.item === 'ore')).toHaveLength(1);
  });

  it('places a shared item at its deepest (longest-path) level', () => {
    // ingot is reachable at depth 1 (via rod) and depth 2 (via plate<-casing).
    const tree = node('product', 5, [
      node('rod', 10, [node('ingot', 10, [node('ore', 10, [], true)])]),
      node('casing', 8, [node('plate', 8, [node('ingot', 8, [node('ore', 8, [], true)])])]),
    ]);
    const g = buildProductionGraph(tree);
    expect(g.nodes.find((n) => n.item === 'ingot')!.level).toBe(3);
  });
});
