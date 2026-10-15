import { describe, expect, it } from 'vitest';
import { isConceptTermNode, isDepthNode, isUnknownEdgeType } from '../A1KnowledgeGraph';

describe('isConceptTermNode (tightened: term: prefix only)', () => {
  it('term: prefix -> true', () => {
    expect(isConceptTermNode({ id: 'term:x' })).toBe(true);
  });

  it('d: depth node -> false (level no longer OR-matched)', () => {
    expect(isConceptTermNode({ id: 'd:a:b', level: 4 })).toBe(false);
  });

  it('plain node -> false', () => {
    expect(isConceptTermNode({ id: '2-1-1', level: 3 })).toBe(false);
  });
});

describe('isDepthNode', () => {
  it('d:{anchor}:{title} -> true', () => {
    expect(isDepthNode('d:a:b')).toBe(true);
  });

  it('term:/serial ids -> false', () => {
    expect(isDepthNode('term:x')).toBe(false);
    expect(isDepthNode('1-1-1')).toBe(false);
  });
});

describe('isUnknownEdgeType（波次三 T4 未知边降级判定）', () => {
  it('六个已知类型 -> false', () => {
    for (const t of ['tree', 'cross', 'semantic', 'constraint', 'migration', 'linkage']) {
      expect(isUnknownEdgeType(t)).toBe(false);
    }
  });

  it('后端未来新增枚举 -> true（触发灰色降级）', () => {
    expect(isUnknownEdgeType('warp')).toBe(true);
    expect(isUnknownEdgeType('resonance')).toBe(true);
  });

  it('空值/缺省 -> true（诚实降级，不冒充已知类型）', () => {
    expect(isUnknownEdgeType('')).toBe(true);
    expect(isUnknownEdgeType(undefined)).toBe(true);
    expect(isUnknownEdgeType(null)).toBe(true);
  });
});
