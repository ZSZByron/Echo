import { describe, expect, it } from 'vitest';
import {
  calculateNodePosition,
  layoutConceptModules,
  TIER_UNGROUPED,
} from '../A1KnowledgeGraph';

describe('calculateNodePosition — depth-tree bands (T12)', () => {
  it('level 4 falls in the L4 band (y=840, below term row y=760)', () => {
    const pos = calculateNodePosition(4, 0, 2, 100);
    expect(pos.y).toBe(840);
    expect(pos.y).toBeGreaterThan(760);
  });

  it('level 5 falls in the L5 band (y=1000) for two-layer trees', () => {
    const pos = calculateNodePosition(5, 0, 1, 0);
    expect(pos.y).toBe(1000);
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
    expect(pos.y).toBe(840);
  });

  it('existing bands unchanged', () => {
    expect(calculateNodePosition(0, 0, 1).y).toBe(-260);
    expect(calculateNodePosition(1, 0, 1).y).toBe(0);
    expect(calculateNodePosition(2, 0, 1).y).toBe(240);
    expect(calculateNodePosition(3, 0, 1, 0).y).toBe(500);
  });
});

describe('layoutConceptModules — tier band columns (T14)', () => {
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
