import { describe, expect, it } from 'vitest';
import { isConceptTermNode, isDepthNode } from '../A1KnowledgeGraph';

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
