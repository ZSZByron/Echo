import { describe, expect, it } from 'vitest';
import {
  BAND_Y,
  calculateNodePosition,
  computeNodeLayout,
  layoutConceptModules,
  NODE_Z_INDEX,
  TIER_UNGROUPED,
} from '../A1KnowledgeGraph';
import type { GraphEdge, GraphNode } from '../../../types/graph';

const mkNode = (id: string, level: number, tier?: number): GraphNode => ({
  id,
  serial_number: id,
  level,
  tier,
  description: `desc ${id}`,
  status: 'completed',
});

const treeEdge = (from: string, to: string): GraphEdge => ({
  from_node_id: from,
  to_node_id: to,
  edge_type: 'tree',
  visual_description: '',
});

/** Bounding boxes do not overlap (edge-touching is allowed). */
const separated = (
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number }
): boolean =>
  a.x + a.width <= b.x ||
  b.x + b.width <= a.x ||
  a.y + a.height <= b.y ||
  b.y + b.height <= a.y;

const expectZeroOverlap = (
  layout: Map<string, { x: number; y: number; width: number; height: number }>
) => {
  const ids = [...layout.keys()];
  for (let i = 0; i < ids.length; i++) {
    for (let j = i + 1; j < ids.length; j++) {
      const a = layout.get(ids[i])!;
      const b = layout.get(ids[j])!;
      expect(
        separated(a, b),
        `nodes ${ids[i]} and ${ids[j]} overlap: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`
      ).toBe(true);
    }
  }
};

/** Build a graph fixture: modules with 5 entries each, depth details, term row. */
const buildFixture = (
  moduleIds: string[],
  moduleTier?: Map<string, number>,
  withDetails = true
): { nodes: GraphNode[]; edges: GraphEdge[] } => {
  const nodes: GraphNode[] = [mkNode('bg', 1)];
  const edges: GraphEdge[] = [];

  moduleIds.forEach(mid => {
    nodes.push(mkNode(mid, 2, moduleTier?.get(mid)));
    edges.push(treeEdge('bg', mid));
    for (let e = 1; e <= 5; e++) {
      const eid = `${mid}-e${e}`;
      nodes.push(mkNode(eid, 3));
      edges.push(treeEdge(mid, eid));
    }
  });

  if (withDetails) {
    // First two modules: first entry gets 3 L4 depth children
    moduleIds.slice(0, 2).forEach(mid => {
      const eid = `${mid}-e1`;
      for (let d = 1; d <= 3; d++) {
        const did = `d:${eid}:detail${d}`;
        nodes.push(mkNode(did, 4));
        edges.push(treeEdge(eid, did));
      }
    });
    // One L5 grandchild under the first L4 of the first module
    const firstL4 = `d:${moduleIds[0]}-e1:detail1`;
    nodes.push(mkNode(`d:${firstL4}:grand`, 5));
    edges.push(treeEdge(firstL4, `d:${firstL4}:grand`));
  }

  // 4 concept-term nodes
  for (let t = 1; t <= 4; t++) {
    nodes.push(mkNode(`term:t${t}`, 4));
  }

  return { nodes, edges };
};

describe('calculateNodePosition — depth-tree bands (T12, updated bands)', () => {
  it('level 4 falls in the L4 band (BAND_Y.L4, below term row BAND_Y.TERM)', () => {
    const pos = calculateNodePosition(4, 0, 2, 100);
    expect(pos.y).toBe(BAND_Y.L4);
    expect(pos.y).toBeGreaterThan(BAND_Y.TERM);
  });

  it('level 5 falls in the L5 band for two-layer trees', () => {
    const pos = calculateNodePosition(5, 0, 1, 0);
    expect(pos.y).toBe(BAND_Y.L5);
  });

  it('L4 siblings group under their parent entry x with DEPTH_SPACING=220', () => {
    const parentX = 340; // e.g. module x + entry offset
    const first = calculateNodePosition(4, 0, 2, parentX);
    const second = calculateNodePosition(4, 1, 2, parentX);
    expect(second.x - first.x).toBe(220);
    // centered on parent x
    expect((first.x + second.x) / 2).toBe(parentX);
  });

  it('L5 siblings group under their L4 parent x the same way', () => {
    const parentX = -120;
    const first = calculateNodePosition(5, 0, 3, parentX);
    const last = calculateNodePosition(5, 2, 3, parentX);
    expect(last.x - first.x).toBe(440);
    expect((first.x + last.x) / 2).toBe(parentX);
  });

  it('no parentX -> falls back to x=0 (only y band applied)', () => {
    const pos = calculateNodePosition(4, 0, 1);
    expect(pos.x).toBe(0);
    expect(pos.y).toBe(BAND_Y.L4);
  });

  it('band order preserved: L0 < L1 < L2 < L3 < TERM < L4 < L5', () => {
    expect(BAND_Y.L0).toBeLessThan(BAND_Y.L1);
    expect(BAND_Y.L1).toBeLessThan(BAND_Y.L2);
    expect(BAND_Y.L2).toBeLessThan(BAND_Y.L3);
    expect(BAND_Y.L3).toBeLessThan(BAND_Y.TERM);
    expect(BAND_Y.TERM).toBeLessThan(BAND_Y.L4);
    expect(BAND_Y.L4).toBeLessThan(BAND_Y.L5);
  });
});

describe('layoutConceptModules — tier band columns (T14, unchanged contract)', () => {
  it('same tier -> same column x, stacked rows', () => {
    const positions = layoutConceptModules([
      { id: '力量体系', tier: 1 },
      { id: '世界本体', tier: 0 },
      { id: '骰子设定', tier: 1 },
    ]);
    const a = positions.get('力量体系')!;
    const b = positions.get('骰子设定')!;
    expect(a.x).toBe(b.x);
    expect(b.y).toBeGreaterThan(a.y);
  });

  it('different tiers -> different columns, ordered tier 0..6', () => {
    const positions = layoutConceptModules([
      { id: 'm0', tier: 0 },
      { id: 'm6', tier: 6 },
      { id: 'm3', tier: 3 },
    ]);
    expect(positions.get('m0')!.x).toBeLessThan(positions.get('m3')!.x);
    expect(positions.get('m3')!.x).toBeLessThan(positions.get('m6')!.x);
  });

  it('undefined tier -> separate 无分组 column placed last', () => {
    const positions = layoutConceptModules([
      { id: 'term:x' },          // no tier
      { id: 'm0', tier: 0 },
      { id: 'm6', tier: 6 },
    ]);
    const ungrouped = positions.get('term:x')!;
    expect(ungrouped.tierBand).toBe(TIER_UNGROUPED);
    expect(ungrouped.x).toBeGreaterThan(positions.get('m6')!.x);
  });

  it('columns centered around x=0', () => {
    const positions = layoutConceptModules([
      { id: 'a', tier: 0 },
      { id: 'b', tier: 1 },
      { id: 'c', tier: 2 },
    ]);
    const xs = [...positions.values()].map(p => p.x);
    expect((Math.min(...xs) + Math.max(...xs)) / 2).toBe(0);
  });
});

describe('computeNodeLayout — zero-overlap invariant (occlusion fix R6)', () => {
  it('fixture A (tree): 6 modules x 5 entries + depth + terms -> no bbox overlap', () => {
    const { nodes, edges } = buildFixture(['m1', 'm2', 'm3', 'm4', 'm5', 'm6']);
    const layout = computeNodeLayout(nodes, edges, 'tree');
    expect(layout.size).toBe(nodes.length);
    expectZeroOverlap(layout);
  });

  it('fixture B (concept): tier2 + tier4 columns -> no bbox overlap', () => {
    const tiers = new Map([
      ['m1', 2], ['m2', 2],
      ['m3', 4], ['m4', 4], ['m5', 4],
    ]);
    const { nodes, edges } = buildFixture(['m1', 'm2', 'm3', 'm4', 'm5'], tiers);
    const layout = computeNodeLayout(nodes, edges, 'concept');
    expect(layout.size).toBe(nodes.length);
    expectZeroOverlap(layout);
  });

  it('fixture C (degenerate): single module single entry -> finite positions, no NaN', () => {
    const { nodes, edges } = buildFixture(['only'], undefined, false);
    const layout = computeNodeLayout(nodes, edges, 'tree');
    expect(layout.size).toBe(nodes.length);
    layout.forEach((box, id) => {
      expect(Number.isFinite(box.x), `${id} x finite`).toBe(true);
      expect(Number.isFinite(box.y), `${id} y finite`).toBe(true);
    });
    expectZeroOverlap(layout);
  });

  it('regression: band order preserved — L3 < term < L4 < L5', () => {
    const { nodes, edges } = buildFixture(['m1', 'm2'], undefined, true);
    const layout = computeNodeLayout(nodes, edges, 'tree');

    const entry = layout.get('m1-e1')!;
    const term = layout.get('term:t1')!;
    const l4 = layout.get(`d:m1-e1:detail1`)!;
    const l5 = layout.get(`d:d:m1-e1:detail1:grand`)!;

    expect(entry.y).toBeLessThan(term.y);
    expect(term.y).toBeLessThan(l4.y);
    expect(l4.y).toBeLessThan(l5.y);
  });

  it('regression: L4 stays below its parent entry, L5 below its L4 parent', () => {
    const { nodes, edges } = buildFixture(['m1'], undefined, true);
    const layout = computeNodeLayout(nodes, edges, 'tree');
    expect(layout.get('d:m1-e1:detail1')!.y).toBeGreaterThan(layout.get('m1-e1')!.y);
    expect(layout.get('d:d:m1-e1:detail1:grand')!.y).toBeGreaterThan(layout.get('d:m1-e1:detail1')!.y);
  });

  it('R2: entry band wider than module spacing no longer overlaps across modules', () => {
    const { nodes, edges } = buildFixture(['m1', 'm2'], undefined, false);
    const layout = computeNodeLayout(nodes, edges, 'tree');
    // Entries of m1 and m2 must not share x ranges
    const m1Entries = [...layout.entries()].filter(([id]) => id.startsWith('m1-e')).map(([, b]) => b);
    const m2Entries = [...layout.entries()].filter(([id]) => id.startsWith('m2-e')).map(([, b]) => b);
    m1Entries.forEach(a => m2Entries.forEach(b => expect(separated(a, b)).toBe(true)));
  });

  it('R4: concept-mode detail bands shift below the deepest tier column', () => {
    const tiers = new Map([['m1', 2], ['m2', 2], ['m3', 4], ['m4', 4], ['m5', 4]]);
    const { nodes, edges } = buildFixture(['m1', 'm2', 'm3', 'm4', 'm5'], tiers);
    const layout = computeNodeLayout(nodes, edges, 'concept');
    // With 3 modules in one tier column, entry band must sit below row 3
    const entry = layout.get('m1-e1')!;
    expect(entry.y).toBeGreaterThanOrEqual(240 + 2 * 220 + 180);
  });

  it('R5: deterministic zIndex per kind', () => {
    const { nodes, edges } = buildFixture(['m1'], undefined, true);
    const layout = computeNodeLayout(nodes, edges, 'tree');
    expect(layout.get('bg')!.zIndex).toBe(NODE_Z_INDEX.L1);
    expect(layout.get('m1')!.zIndex).toBe(NODE_Z_INDEX.L2);
    expect(layout.get('m1-e1')!.zIndex).toBe(NODE_Z_INDEX.L3);
    expect(layout.get('term:t1')!.zIndex).toBe(NODE_Z_INDEX.term);
    expect(layout.get('d:m1-e1:detail1')!.zIndex).toBe(NODE_Z_INDEX.L4);
    expect(layout.get('d:d:m1-e1:detail1:grand')!.zIndex).toBe(NODE_Z_INDEX.L5);
  });
});
