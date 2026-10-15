/**
 * A1KnowledgeGraph 边类型渲染测试（波次三 T4 守门）
 *
 * 覆盖（施工单 QA：迁移边渲染/衔接边渲染/未知边降级）：
 * 1. migration 边 → ▶ 标签 + edge-migration 类（橙红实线）
 * 2. linkage 边 → ⇄ 标签 + edge-linkage 类（青色虚线）
 * 3. 未知边类型 → 灰色降级 + 「未知边类型」标签 + edge-unknown 类，不冒充 legacy cross
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import {
  A1KnowledgeGraph,
  edgeVisualStyle,
  type A1KnowledgeGraphProps,
} from '../graph/A1KnowledgeGraph';
import type { KnowledgeGraph, GraphEdge } from '../../types/graph';

// ResizeObserver stub for jsdom (required by React Flow) —— 沿用 A1KnowledgeGraph.test.tsx 惯例
class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

declare global {
  interface Window {
    ResizeObserver: typeof ResizeObserverStub;
  }
}

beforeEach(() => {
  window.ResizeObserver = ResizeObserverStub;
});

const mkGraph = (extraEdges: GraphEdge[]): KnowledgeGraph => ({
  scene_id: 's-edge',
  background_node_id: 'bg',
  nodes: {
    bg: { id: 'bg', serial_number: '1', level: 1, description: 'World', status: 'completed' },
    m1: { id: 'm1', serial_number: '1-1', level: 2, description: 'Mod A', status: 'completed' },
    m2: { id: 'm2', serial_number: '1-2', level: 2, description: 'Mod B', status: 'completed' },
  },
  edges: [
    { from_node_id: 'bg', to_node_id: 'm1', edge_type: 'tree', visual_description: '' },
    { from_node_id: 'bg', to_node_id: 'm2', edge_type: 'tree', visual_description: '' },
    ...extraEdges,
  ],
});

const renderGraph = (edges: GraphEdge[]) => {
  const props: A1KnowledgeGraphProps = {
    graph: mkGraph(edges),
    isLoading: false,
    error: null,
  };
  return render(<A1KnowledgeGraph {...props} />);
};

describe('edgeVisualStyle 新边样式判定（波次三 T4，纯函数）', () => {
  it('migration 边 → ▶ 标签 + edge-migration + 橙红实线 + animated', () => {
    const v = edgeVisualStyle({
      from_node_id: 'm1',
      to_node_id: 'm2',
      edge_type: 'migration',
      visual_description: '从战后废墟到重建之城',
      relation: '迁移',
      confidence: '',
      confirmed: true,
    });

    expect(v.className).toBe('edge-migration');
    expect(v.label).toContain('▶');
    expect(v.label).toContain('从战后废墟到重建之城');
    expect(v.edgeStyle.stroke).toBe('#ef4444');
    expect(v.animated).toBe(true);
  });

  it('linkage 边 → ⇄ 标签 + edge-linkage + 青色虚线', () => {
    const v = edgeVisualStyle({
      from_node_id: 'm1',
      to_node_id: 'm2',
      edge_type: 'linkage',
      visual_description: '威望·上升',
      relation: '衔接',
      confidence: '',
      confirmed: true,
    });

    expect(v.className).toBe('edge-linkage');
    expect(v.label).toContain('⇄');
    expect(v.label).toContain('威望·上升');
    expect(v.edgeStyle.stroke).toBe('#06b6d4');
    expect(v.edgeStyle.strokeDasharray).toBe('5,3');
  });

  it('未知边类型 → 灰色降级 + 「未知边类型」标签，不冒充 legacy cross', () => {
    // 模拟后端未来新增枚举直透前端（s2-unknown-enum-degrade 场景）——
    // 运行时值超出前端类型联合，构造 fixture 需越过类型层（测试语义本身）
    const warpEdge = {
      from_node_id: 'm1',
      to_node_id: 'm2',
      edge_type: 'warp' as unknown as GraphEdge['edge_type'],
      visual_description: '跃迁',
      relation: '',
      confidence: '',
    } as GraphEdge;

    const v = edgeVisualStyle(warpEdge);

    expect(v.className).toBe('edge-unknown');
    expect(v.className).not.toBe('edge-cross');
    expect(v.label).toContain('未知边类型');
    expect(v.label).toContain('warp');
    expect(v.edgeStyle.stroke).toBe('#4b5563');
  });
});

describe('A1KnowledgeGraph 混合新边渲染冒烟（波次三 T4）', () => {
  it('migration/linkage/未知边混合图 → 组件渲染不崩溃，节点在', () => {
    const warpEdge = {
      from_node_id: 'bg',
      to_node_id: 'm2',
      edge_type: 'warp' as unknown as GraphEdge['edge_type'],
      visual_description: '跃迁',
      relation: '',
      confidence: '',
    } as GraphEdge;

    renderGraph([
      {
        from_node_id: 'm1',
        to_node_id: 'm2',
        edge_type: 'migration',
        visual_description: '从战后到重建',
        relation: '迁移',
        confidence: '',
        confirmed: true,
      },
      {
        from_node_id: 'bg',
        to_node_id: 'm2',
        edge_type: 'linkage',
        visual_description: '威望·上升',
        relation: '衔接',
        confidence: '',
        confirmed: true,
      },
      warpEdge,
    ]);

    // 节点在 jsdom 可渲染（既有惯例）；边 SVG 不渲染（edgeVisualStyle 纯函数已守门）
    expect(document.querySelectorAll('.react-flow__node').length).toBeGreaterThanOrEqual(3);
  });
});
