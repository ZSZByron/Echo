/**
 * EdgeReviewPanel Component Tests
 *
 * T-C: Right-side concept edge review list with tri-state grouping,
 * inline confirm/reject, rejected collapse, confirmed highlight, empty state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EdgeReviewPanel, getEdgeKey, classifyEdge } from '../graph/EdgeReviewPanel';
import type { GraphEdge } from '../../types/graph';

const termNodeLabels = {
  'term:死亡转生': '死亡转生',
  'term:灵魂契约': '灵魂契约',
  'term:血月': '血月',
};

const makeEdge = (overrides: Partial<GraphEdge>): GraphEdge => ({
  from_node_id: 'term:死亡转生',
  to_node_id: 'term:灵魂契约',
  edge_type: 'tree' as GraphEdge['edge_type'],
  visual_description: 'AI 推断：转生需要灵魂作为媒介',
  ...overrides,
});

const pendingEdge = makeEdge({
  edge_type: 'tree',
  confidence: 'semantic',
  confirmed: false,
  relation: '触发',
});

const confirmedEdge = makeEdge({
  from_node_id: 'term:血月',
  to_node_id: 'term:死亡转生',
  confidence: 'semantic',
  confirmed: true,
  relation: '预示',
  visual_description: '血月之夜死亡转生频率上升',
});

const rejectedEdge = makeEdge({
  from_node_id: 'term:灵魂契约',
  to_node_id: 'term:血月',
  confidence: 'semantic',
  confirmed: false,
  relation: '禁止',
});

describe('EdgeReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders tri-state groups with counts', () => {
    const rejectedKeys = { [getEdgeKey(rejectedEdge)]: { from_node_id: 'x' } };
    render(
      <EdgeReviewPanel
        edges={[pendingEdge, confirmedEdge, rejectedEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
        rejectedKeys={rejectedKeys}
      />
    );
    expect(screen.getByText(/待确认 \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/已确认 \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/已拒绝 \(1\)/)).toBeInTheDocument();
  });

  it('shows concept terms and relation per entry', () => {
    render(
      <EdgeReviewPanel
        edges={[pendingEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
      />
    );
    expect(screen.getAllByText('死亡转生').length).toBeGreaterThan(0);
    expect(screen.getAllByText('灵魂契约').length).toBeGreaterThan(0);
    expect(screen.getByText('[触发]')).toBeInTheDocument();
  });

  it('calls onConfirm with slash-separated key on inline ✓', () => {
    const onConfirm = vi.fn();
    render(
      <EdgeReviewPanel
        edges={[pendingEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={onConfirm}
        onReject={vi.fn()}
      />
    );
    fireEvent.click(screen.getByLabelText(`确认 ${getEdgeKey(pendingEdge)}`));
    expect(onConfirm).toHaveBeenCalledWith('term:死亡转生/term:灵魂契约/触发');
  });

  it('calls onReject with slash-separated key on inline ✗', () => {
    const onReject = vi.fn();
    render(
      <EdgeReviewPanel
        edges={[pendingEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={onReject}
      />
    );
    fireEvent.click(screen.getByLabelText(`拒绝 ${getEdgeKey(pendingEdge)}`));
    expect(onReject).toHaveBeenCalledWith('term:死亡转生/term:灵魂契约/触发');
  });

  it('collapses rejected group by default and expands on header click', () => {
    const rejectedKeys = { [getEdgeKey(rejectedEdge)]: {} };
    render(
      <EdgeReviewPanel
        edges={[rejectedEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
        rejectedKeys={rejectedKeys}
      />
    );
    // Collapsed: entry hidden
    expect(screen.queryByText('灵魂契约')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/已拒绝 \(1\)/));
    // Expanded: entry visible
    expect(screen.getAllByText('灵魂契约').length).toBeGreaterThan(0);
  });

  it('renders confirmed entry with highlight styles and badge instead of buttons', () => {
    render(
      <EdgeReviewPanel
        edges={[confirmedEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
      />
    );
    const item = screen.getByText('已确认', { selector: 'span' });
    expect(item).toBeInTheDocument();
    // No inline action buttons for confirmed edges
    expect(screen.queryByLabelText(/确认 term:/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/拒绝 term:/)).not.toBeInTheDocument();
  });

  it('renders empty state text when no edges', () => {
    render(
      <EdgeReviewPanel
        edges={[]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
      />
    );
    expect(screen.getByText('暂无概念边——定稿后 AI 将从你的设定中提取概念关联网')).toBeInTheDocument();
  });

  describe('helpers', () => {
    it('getEdgeKey uses slash separator', () => {
      expect(getEdgeKey(pendingEdge)).toBe('term:死亡转生/term:灵魂契约/触发');
    });

    it('classifyEdge respects confirmed/pending/rejected', () => {
      expect(classifyEdge(confirmedEdge)).toBe('confirmed');
      expect(classifyEdge(pendingEdge)).toBe('pending');
      const key = getEdgeKey(pendingEdge);
      expect(classifyEdge(pendingEdge, { [key]: {} })).toBe('rejected');
    });
  });
});
