/**
 * NodeDetailPanel Tests
 *
 * Covers: buildCrosslinks (hit / self-exclusion / longest-first),
 * searchGraphNodes, nodeTitle extraction, and panel rendering
 * (L3 full answer, d: content, related edges, crosslink navigation).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NodeDetailPanel, {
  buildCrosslinks,
  searchGraphNodes,
  nodeTitle,
  nodeKindLabel,
} from '../NodeDetailPanel';
import type { KnowledgeGraph, GraphNode, GraphEdge } from '../../types/graph';

const mkNode = (id: string, level: number, description: string, tier?: number): GraphNode => ({
  id,
  serial_number: id,
  level,
  ...(tier !== undefined ? { tier } : {}),
  description,
  status: 'completed',
});

describe('buildCrosslinks', () => {
  const terms = [
    { term: '明华世界', nodeId: 'd:a:明华世界' },
    { term: '名称与概念', nodeId: 'entry-1' },
    { term: '明华', nodeId: 'd:b:明华' },
  ];

  it('marks occurrences of other titles as crosslinks', () => {
    const segs = buildCrosslinks('这是明华世界的设定', terms, 'self');
    const linked = segs.filter(s => s.nodeId);
    expect(linked).toEqual([{ text: '明华世界', nodeId: 'd:a:明华世界' }]);
    expect(segs[0].text).toBe('这是');
    expect(segs[segs.length - 1].text).toBe('的设定');
  });

  it('excludes self references (own title is not a link)', () => {
    const segs = buildCrosslinks('名称与概念是核心', terms, 'entry-1');
    expect(segs.every(s => s.nodeId !== 'entry-1')).toBe(true);
    expect(segs.map(s => s.text).join('')).toBe('名称与概念是核心');
  });

  it('prefers the longest term (明华世界 wins over its prefix 明华)', () => {
    const segs = buildCrosslinks('明华世界', terms, 'self');
    expect(segs).toEqual([{ text: '明华世界', nodeId: 'd:a:明华世界' }]);
  });

  it('returns a single plain segment when nothing matches', () => {
    expect(buildCrosslinks('普通文本', terms, 'self')).toEqual([{ text: '普通文本' }]);
  });

  it('regex-escapes special characters in terms', () => {
    const segs = buildCrosslinks('a(b) c', [{ term: 'a(b)', nodeId: 'n1' }], 'self');
    expect(segs.filter(s => s.nodeId)).toEqual([{ text: 'a(b)', nodeId: 'n1' }]);
  });
});

describe('searchGraphNodes', () => {
  const graph: KnowledgeGraph = {
    scene_id: 's',
    nodes: {
      'entry-1': mkNode('entry-1', 3, '名称与概念: 由明珠映照出的大道印痕'),
      'mod-1': mkNode('mod-1', 2, '地理模块'),
      'd:a:明华世界': mkNode('d:a:明华世界', 4, '明华世界是力量本源'),
    },
    edges: [],
  };

  it('matches title and description case-insensitively with a ±12 char snippet', () => {
    const hits = searchGraphNodes('名称与概念', graph);
    expect(hits).toHaveLength(1);
    expect(hits[0].nodeId).toBe('entry-1');
    expect(hits[0].title).toBe('名称与概念');
    expect(hits[0].snippet).toContain('由明珠映照出的');

    const byContent = searchGraphNodes('力量本源', graph);
    expect(byContent[0].nodeId).toBe('d:a:明华世界');
  });

  it('returns at most 10 hits and empty for blank queries', () => {
    expect(searchGraphNodes('  ', graph)).toEqual([]);
    const big: KnowledgeGraph = {
      scene_id: 's',
      nodes: Object.fromEntries(
        Array.from({ length: 15 }, (_, i) => [`n${i}`, mkNode(`n${i}`, 3, `关键词条目${i}`)])
      ),
      edges: [],
    };
    expect(searchGraphNodes('关键词', big)).toHaveLength(10);
  });
});

describe('nodeTitle / nodeKindLabel extraction', () => {
  it('d: → id title segment; L3 → field name; L2 → module name; cst → id', () => {
    expect(nodeTitle(mkNode('d:anchor:明华世界', 4, 'x'))).toBe('明华世界');
    expect(nodeTitle(mkNode('e1', 3, '名称与概念: 正文'))).toBe('名称与概念');
    expect(nodeTitle(mkNode('m1', 2, '地理模块'))).toBe('地理模块');
    expect(nodeTitle(mkNode('cst_law_1', 0, '[A1] Constraint(LAW.x=y)'))).toBe('cst_law_1');
    expect(nodeKindLabel(mkNode('d:a:b', 4, 'x'))).toBe('深度条目');
  });
});

describe('NodeDetailPanel rendering', () => {
  const edges: GraphEdge[] = [
    {
      from_node_id: 'mod-1',
      to_node_id: 'entry-1',
      edge_type: 'tree',
      visual_description: 'contains',
    },
    {
      from_node_id: 'entry-1',
      to_node_id: 'd:a:明华世界',
      edge_type: 'cross',
      visual_description: 'derives',
      confidence: 'semantic',
      confirmed: false,
    },
  ];
  const graph: KnowledgeGraph = {
    scene_id: 's',
    nodes: {
      'mod-1': mkNode('mod-1', 2, '地理模块', 1),
      'entry-1': mkNode('entry-1', 3, '名称与概念: 由明珠映照出的大道印痕，明华世界的本源'),
      'd:a:明华世界': mkNode('d:a:明华世界', 4, '明华世界是力量本源'),
    },
    edges,
  };

  it('renders null without a selected node', () => {
    const { container } = render(<NodeDetailPanel node={null} graph={graph} />);
    expect(container.querySelector('[data-testid="node-detail-panel"]')).toBeNull();
  });

  it('shows L3 field name + full answer text and the parent module', () => {
    render(
      <NodeDetailPanel node={graph.nodes['entry-1']} graph={graph} />
    );
    expect(screen.getByTestId('node-detail-title').textContent).toBe('名称与概念');
    expect(screen.getByTestId('node-detail-body').textContent).toContain('由明珠映照出的大道印痕');
    expect(screen.getByTestId('node-detail-panel').textContent).toContain('地理模块');
  });

  it('shows d: title + full content, related edges with status badges', () => {
    render(
      <NodeDetailPanel node={graph.nodes['d:a:明华世界']} graph={graph} />
    );
    expect(screen.getByTestId('node-detail-title').textContent).toBe('明华世界');
    expect(screen.getByTestId('node-detail-body').textContent).toContain('力量本源');
    const related = screen.getAllByTestId('node-detail-related-edge');
    expect(related).toHaveLength(1);
    // pending semantic badge
    expect(screen.getByTestId('node-detail-panel').textContent).toContain('待确认');
  });

  it('renders crosslinks for other titles in the body and navigates on click', () => {
    const onNavigate = vi.fn();
    render(
      <NodeDetailPanel node={graph.nodes['entry-1']} graph={graph} onNavigate={onNavigate} />
    );
    // Body contains 明华世界 (another d: node's title) → crosslink, not plain text
    const links = screen.getAllByTestId('content-crosslink');
    const target = links.find(l => l.textContent === '明华世界');
    expect(target).toBeDefined();
    fireEvent.click(target!);
    expect(onNavigate).toHaveBeenCalledWith('d:a:明华世界');
  });

  it('navigates to the peer node when clicking a related edge', () => {
    const onNavigate = vi.fn();
    render(
      <NodeDetailPanel node={graph.nodes['d:a:明华世界']} graph={graph} onNavigate={onNavigate} />
    );
    fireEvent.click(screen.getAllByTestId('node-detail-related-edge')[0]);
    expect(onNavigate).toHaveBeenCalledWith('entry-1');
  });

  it('close button calls onClose', () => {
    const onClose = vi.fn();
    render(<NodeDetailPanel node={graph.nodes['mod-1']} graph={graph} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('node-detail-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
