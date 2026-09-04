import { describe, expect, it } from 'vitest';
import { calculateNodePosition } from '../A1KnowledgeGraph';

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
