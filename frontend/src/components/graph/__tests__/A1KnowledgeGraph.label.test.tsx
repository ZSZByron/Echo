import { describe, expect, it } from 'vitest';
import {
  buildAnchorFieldLabel,
  depthEntrySummary,
  depthNodeLabel,
} from '../A1KnowledgeGraph';
import type { GraphNode } from '../../../types/graph';

const mkNode = (
  id: string,
  level: number,
  description: string
): GraphNode => ({
  id,
  serial_number: id,
  level,
  description,
  status: 'completed',
});

describe('buildAnchorFieldLabel — L3 anchor id → field name', () => {
  it('maps L3 entry ids (contain ".", no d:/term:/cst_/bg_ prefix) to field label', () => {
    const nodes = [
      mkNode('IP定位.concept', 3, '核心概念: 正本清源，每个人的修仙'),
      mkNode('IP定位.name', 3, '明华世界: 修仙世界的名称'),
      mkNode('d:IP定位.concept:核心概念', 4, '正文内容'),
      mkNode('term:灵气', 4, '灵气'),
      mkNode('cst_red_1', 0, 'RED:禁止:xxx'),
      mkNode('bg_world', 1, '世界背景'),
      mkNode('m0', 2, '模块描述'),
    ];
    expect(buildAnchorFieldLabel(nodes)).toEqual({
      'IP定位.concept': '核心概念',
      'IP定位.name': '明华世界',
    });
  });

  it('uses whole description when no colon present', () => {
    const nodes = [mkNode('IP定位.essence', 3, '本质要素')];
    expect(buildAnchorFieldLabel(nodes)).toEqual({ 'IP定位.essence': '本质要素' });
  });
});

describe('depthEntrySummary — first clause clamped to 10 chars', () => {
  it('returns first clause before comma/period', () => {
    expect(depthEntrySummary('正本清源，每个人的修仙。')).toBe('正本清源');
  });
  it('clamps long first clause to 10 chars + ellipsis', () => {
    const long = '这是一个超过十个字的非常长的首句子内容确实很长';
    expect(depthEntrySummary(long)).toBe('这是一个超过十个字的…');
  });
});

describe('depthNodeLabel — same-name fallback (label dedup fix)', () => {
  const anchorFieldLabel = {
    'IP定位.concept': '核心概念',
  };

  it('same-name d: node renders content summary, NOT the duplicated field name', () => {
    const node = mkNode(
      'd:IP定位.concept:核心概念',
      4,
      '正本清源，每个人的修仙都要经历三转。'
    );
    const label = depthNodeLabel(node, anchorFieldLabel);
    expect(label).toContain('正本清源');
    expect(label).not.toBe('▸ 核心概念');
    expect(label).not.toContain('▸ 核心概念');
  });

  it('non-same-name d: node keeps the "▸ {title}" form', () => {
    const node = mkNode(
      'd:IP定位.name:明华世界',
      4,
      '明华世界是修仙的大世界，灵气充沛。'
    );
    expect(depthNodeLabel(node, anchorFieldLabel)).toBe('▸ 明华世界');
  });

  it('title containing colons is preserved via slice(2).join', () => {
    const node = mkNode('d:IP定位.concept:别名:旧称', 4, '别名说明。');
    expect(depthNodeLabel(node, {})).toBe('▸ 别名:旧称');
  });
});
