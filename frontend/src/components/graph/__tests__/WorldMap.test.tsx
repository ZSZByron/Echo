/**
 * WorldMap 活地图七大陆视图测试（波次三 T2 守门，拍3-3）
 *
 * 覆盖（施工单 QA：渲染/空状态/已答亮起）：
 * 1. 空图 → 七大陆标题全渲染 + 未答大陆灰态「尚未触及」+ 总点亮 0
 * 2. 已答 L2 → 对应大陆亮起（N 处 + 条目列表）
 * 3. graph=null → 优雅降级，七大陆仍渲染
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorldMap } from '../WorldMap';
import type { KnowledgeGraph, GraphNode } from '../../../types/graph';

const L2 = (id: string, serial: string, desc: string): GraphNode => ({
  id,
  serial_number: serial,
  level: 2,
  description: desc,
  status: 'completed',
});

const graphWith = (nodes: GraphNode[]): KnowledgeGraph => ({
  scene_id: 's-e2e',
  background_node_id: 'bg',
  nodes: Object.fromEntries(nodes.map(n => [n.id, n])),
  edges: [],
});

describe('WorldMap 活地图七大陆（波次三 T2）', () => {
  it('空图 → 七大陆标题全渲染 + 未答灰态 + 已点亮 0 处', () => {
    render(<WorldMap graph={graphWith([])} />);

    for (const label of ['IP 定位', '世界观', '剧情', '角色', '玩法', '视觉', '设定边界']) {
      expect(screen.getByText(new RegExp(label))).toBeTruthy();
    }
    // 七大陆卡片 testid 全在
    for (const cid of ['ip', 'worldview', 'story_line', 'character', 'gameplay', 'visual', 'setting_boundary']) {
      expect(screen.getByTestId(`continent-${cid}`)).toBeTruthy();
    }
    // 七大陆全部灰态（未答大陆各显示一处「尚未触及」）
    expect(screen.getAllByText(/尚未触及/)).toHaveLength(7);
    expect(screen.getByText(/已点亮 0 处/)).toBeTruthy();
  });

  it('已答 L2 → 对应大陆亮起并展示条目与计数', () => {
    render(
      <WorldMap
        graph={graphWith([
          L2('m-2-1', '2-1', '地理模块：环形群岛'),
          L2('m-2-2', '2-2', '文化模块：星歌部落'),
        ])}
      />
    );

    // serial 前缀 2-* → 世界观大陆：2 处 + 两个模块名
    const worldview = screen.getByTestId('continent-worldview');
    expect(worldview.textContent).toContain('2 处');
    expect(worldview.textContent).toContain('地理模块');
    expect(worldview.textContent).toContain('文化模块');
    expect(screen.getByText(/已点亮 2 处/)).toBeTruthy();
    // 未答大陆仍灰态
    expect(screen.getByTestId('continent-ip').textContent).toContain('尚未触及');
  });

  it('graph=null → 优雅降级，七大陆仍渲染且零点亮', () => {
    render(<WorldMap graph={null} />);

    expect(screen.getByTestId('continent-worldview')).toBeTruthy();
    expect(screen.getByTestId('continent-setting_boundary')).toBeTruthy();
    expect(screen.getByText(/已点亮 0 处/)).toBeTruthy();
  });
});
