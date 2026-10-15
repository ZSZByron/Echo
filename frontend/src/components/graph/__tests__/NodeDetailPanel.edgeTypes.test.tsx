/**
 * NodeDetailPanel 新边属性展示测试（波次三 T4 守门）
 *
 * 覆盖：迁移边/衔接边在详情面板关联条目行展示边类型标签，
 * 并以 title tooltip 透出 visual_description（trigger / dimension·direction 载体）。
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import NodeDetailPanel from '../NodeDetailPanel';
import type { KnowledgeGraph, GraphEdge } from '../../../types/graph';

const NODE = { id: 'm1', serial_number: '1-1', level: 2, description: '模块', status: 'completed' } as const;

const graphWith = (edge: GraphEdge): KnowledgeGraph => ({
  scene_id: 's-panel',
  background_node_id: 'bg',
  nodes: {
    bg: { id: 'bg', serial_number: '1', level: 1, description: 'World', status: 'completed' },
    m1: { ...NODE },
    m2: { id: 'm2', serial_number: '1-2', level: 2, description: 'Mod B', status: 'completed' },
  },
  // 仅保留目标边（不挂 tree 边），保证关联条目行唯一可断言
  edges: [edge],
});

describe('NodeDetailPanel 新边属性（波次三 T4）', () => {
  it('migration 边 → 关联条目行带「迁移（从→到）」类型标签 + tooltip 透出 visual_description', () => {
    render(
      <NodeDetailPanel
        node={{ ...NODE }}
        graph={graphWith({
          from_node_id: 'm1',
          to_node_id: 'm2',
          edge_type: 'migration',
          visual_description: '触发：七年之约到期',
          relation: '迁移',
          confidence: '',
          confirmed: true,
        })}
      />
    );

    expect(screen.getByTestId('node-detail-edge-type').textContent).toContain('迁移（从→到）');
    const row = screen.getByTestId('node-detail-related-edge');
    expect(row.getAttribute('title')).toBe('触发：七年之约到期');
  });

  it('linkage 边 → 「衔接（维度·方向）」类型标签', () => {
    render(
      <NodeDetailPanel
        node={{ ...NODE }}
        graph={graphWith({
          from_node_id: 'm2',
          to_node_id: 'm1',
          edge_type: 'linkage',
          visual_description: '威望·上升（幅度 3）',
          relation: '衔接',
          confidence: '',
          confirmed: true,
        })}
      />
    );

    expect(screen.getByTestId('node-detail-edge-type').textContent).toContain('衔接（维度·方向）');
    const row = screen.getByTestId('node-detail-related-edge');
    expect(row.getAttribute('title')).toBe('威望·上升（幅度 3）');
  });
});
