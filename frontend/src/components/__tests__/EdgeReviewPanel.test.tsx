/**
 * EdgeReviewPanel Component Tests
 *
 * T-C: Right-side concept edge review list with tri-state grouping,
 * inline confirm/reject, rejected collapse, confirmed highlight, empty state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EdgeReviewPanel, getEdgeKey, classifyEdge, isNewRelationEdge } from '../graph/EdgeReviewPanel';
import type { GraphEdge } from '../../types/graph';
import type { ConceptTerm, ProposedRelation } from '../../types/a1';

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

describe('EdgeReviewPanel — Concept Term Group (T-D)', () => {
  const conceptTerms: ConceptTerm[] = [
    { term: '死亡转生', field_key: 'world.rules', gloss: '死后转生', confirmed: false },
    { term: '灵魂契约', field_key: 'world.rules', gloss: '灵魂交易', confirmed: true },
    { term: '血月', field_key: 'scene.events', gloss: '红色之月', confirmed: false },
  ];

  const proposedRelations: ProposedRelation[] = [
    { name: '触发', from_term: '死亡转生', to_term: '灵魂契约', rationale: '转生需要契约媒介' },
  ];

  const renderPanel = (overrides: Record<string, unknown> = {}) =>
    render(
      <EdgeReviewPanel
        edges={[pendingEdge, confirmedEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
        conceptTerms={conceptTerms}
        proposedRelations={proposedRelations}
        onConfirmTerm={vi.fn()}
        onConfirmAllTerms={vi.fn()}
        onExtractRelations={vi.fn()}
        {...overrides}
      />
    );

  it('renders concept term group with confirmed count', () => {
    renderPanel();
    expect(screen.getByText('概念词（已确认 1/3）')).toBeInTheDocument();
    expect(screen.getAllByTestId('concept-term-row')).toHaveLength(3);
    expect(screen.getByText('✓ 已确认')).toBeInTheDocument();
  });

  it('calls onConfirmTerm with the term on single ✓确认', () => {
    const onConfirmTerm = vi.fn();
    renderPanel({ onConfirmTerm });
    fireEvent.click(screen.getByLabelText('确认概念词 死亡转生'));
    expect(onConfirmTerm).toHaveBeenCalledWith('死亡转生');
  });

  it('calls onConfirmAllTerms on 全部确认', () => {
    const onConfirmAllTerms = vi.fn();
    renderPanel({ onConfirmAllTerms });
    fireEvent.click(screen.getByTestId('confirm-all-terms'));
    expect(onConfirmAllTerms).toHaveBeenCalledTimes(1);
  });

  it('extract button is disabled with hint when confirmed < 2', () => {
    renderPanel();
    const btn = screen.getByTestId('extract-relations') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(screen.getByText(/确认至少 2 个概念词/)).toBeInTheDocument();
  });

  it('extract button enabled and calls onExtractRelations when confirmed >= 2', () => {
    const onExtractRelations = vi.fn();
    renderPanel({
      onExtractRelations,
      conceptTerms: conceptTerms.map(t => ({ ...t, confirmed: true })),
    });
    const btn = screen.getByTestId('extract-relations') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
    fireEvent.click(btn);
    expect(onExtractRelations).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner state while isExtracting', () => {
    renderPanel({
      isExtracting: true,
      conceptTerms: conceptTerms.map(t => ({ ...t, confirmed: true })),
    });
    expect(screen.getByText('提取中...')).toBeInTheDocument();
    const btn = screen.getByTestId('extract-relations') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('shows [新关系] amber badge on pending proposed edge', () => {
    renderPanel();
    expect(screen.getByTestId('new-relation-badge')).toBeInTheDocument();
  });

  it('does not show [新关系] badge when relation not in proposedRelations', () => {
    renderPanel({ proposedRelations: [] });
    expect(screen.queryByTestId('new-relation-badge')).not.toBeInTheDocument();
  });

  it('badge disappears once the edge is confirmed (no badge in confirmed entry)', () => {
    render(
      <EdgeReviewPanel
        edges={[confirmedEdge]}
        nodeLabels={termNodeLabels}
        onConfirm={vi.fn()}
        onReject={vi.fn()}
        conceptTerms={conceptTerms}
        proposedRelations={[
          { name: '预示', from_term: '血月', to_term: '死亡转生', rationale: 'x' },
        ]}
      />
    );
    expect(screen.queryByTestId('new-relation-badge')).not.toBeInTheDocument();
  });

  it('hides concept group when conceptTerms is empty/undefined', () => {
    renderPanel({ conceptTerms: [] });
    expect(screen.queryByTestId('concept-term-group')).not.toBeInTheDocument();
    expect(screen.queryByTestId('extract-relations')).not.toBeInTheDocument();
  });

  it('isNewRelationEdge matches relation + term endpoints', () => {
    expect(isNewRelationEdge(pendingEdge, proposedRelations)).toBe(true);
    expect(isNewRelationEdge(pendingEdge, [])).toBe(false);
    expect(
      isNewRelationEdge(pendingEdge, [
        { name: '触发', from_term: '别的', to_term: '灵魂契约', rationale: '' },
      ])
    ).toBe(false);
  });
});
