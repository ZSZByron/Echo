/**
 * EdgeReviewPanel Component
 *
 * Right-side review panel for concept edges (概念网审核清单).
 * Each entry = one concept edge with color-coded status:
 * - Amber = pending confirmation (待确认)
 * - Green = confirmed (已确认)
 * - Gray  = rejected (已拒绝, collapsed by default, expandable)
 *
 * Bidirectional linking with canvas:
 * - highlightKey prop scrolls to & flashes the matching entry
 * - onHoverEdge highlights the matching canvas edge
 *
 * Task T-C. Zero text input (no input/textarea/contentEditable).
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { GraphEdge } from '../../types/graph';
import type { ConceptTerm, ProposedRelation } from '../../types/a1';

export interface EdgeReviewPanelProps {
  /** Concept edges to review (semantic/rule/structure) */
  edges: GraphEdge[];
  /** node_id -> concept term label for endpoint display */
  nodeLabels: Record<string, string>;
  /** Workspace file id (passed through for API parity) */
  fileId?: string;
  /** Confirm an edge by key (`from/to/relation`, slash-separated) */
  onConfirm: (edgeKey: string) => void;
  /** Reject an edge by key */
  onReject: (edgeKey: string) => void;
  /** Edge key to scroll into view & flash (from canvas edge click) */
  highlightKey?: string | null;
  /** Canvas hover sync: hover an entry to highlight its edge */
  onHoverEdge?: (edgeKey: string | null) => void;
  /** Keys of rejected edges (from workspace rejected_edges record) */
  rejectedKeys?: Record<string, unknown>;
  /** Concept terms for the confirm group (T-D; hidden when empty) */
  conceptTerms?: ConceptTerm[];
  /** Proposed relations from LLM extraction (T-D; drives [新关系] badges) */
  proposedRelations?: ProposedRelation[];
  /** Confirm a single concept term into dictionary */
  onConfirmTerm?: (term: string) => void;
  /** Confirm all concept terms at once */
  onConfirmAllTerms?: () => void;
  /** Trigger LLM concept-edge extraction */
  onExtractRelations?: () => void;
  /** True while extract-edges LLM call is in flight */
  isExtracting?: boolean;
}

/** Canonical edge key: `from/to/relation` (slash-separated). */
export function getEdgeKey(edge: GraphEdge): string {
  return `${edge.from_node_id}/${edge.to_node_id}/${edge.relation || edge.visual_description}`;
}

/**
 * T-D: edge whose relation comes from LLM extraction of concept terms
 * (matches a proposed_relations entry by relation name + term endpoints).
 * Badge shows only while pending — once confirmed the relation word is
 * dictionary-backed, so the badge disappears.
 */
export function isNewRelationEdge(edge: GraphEdge, proposedRelations?: ProposedRelation[]): boolean {
  if (!proposedRelations || proposedRelations.length === 0) return false;
  const relation = edge.relation || edge.visual_description;
  return proposedRelations.some(
    p =>
      p.name === relation &&
      edge.from_node_id === `term:${p.from_term}` &&
      edge.to_node_id === `term:${p.to_term}`
  );
}

export type EdgeReviewStatus = 'pending' | 'confirmed' | 'rejected';

/** Classify an edge into review status (defensive: rejected list wins). */
export function classifyEdge(edge: GraphEdge, rejectedKeys?: Record<string, unknown>): EdgeReviewStatus {
  const key = getEdgeKey(edge);
  if (rejectedKeys && key in rejectedKeys) return 'rejected';
  if (edge.confirmed === true) return 'confirmed';
  if (edge.confirmed === false && edge.confidence === 'semantic') return 'pending';
  if (edge.confirmed === false) return 'rejected';
  return 'confirmed';
}

/** Dictionary-tier badge: ★ rule (green) / ◆ semantic (amber) / ◇ structure (blue-gray). */
function tierBadge(edge: GraphEdge): { symbol: string; className: string; title: string } {
  if (edge.confidence === 'rule') {
    return { symbol: '★', className: 'text-emerald-400', title: '铁律推断' };
  }
  if (edge.confidence === 'structure') {
    return { symbol: '◇', className: 'text-gray-400', title: '结构拆解' };
  }
  return { symbol: '◆', className: 'text-amber-400', title: '联想' };
}

const STATUS_GROUPS: Array<{ status: EdgeReviewStatus; title: string; borderClass: string; textClass: string }> = [
  { status: 'pending', title: '待确认', borderClass: 'border-l-4 border-amber-400', textClass: 'text-amber-300' },
  { status: 'confirmed', title: '已确认', borderClass: 'border-l-4 border-emerald-500', textClass: 'text-emerald-300' },
  { status: 'rejected', title: '已拒绝', borderClass: 'border-l-4 border-gray-600', textClass: 'text-gray-400' },
];

export function EdgeReviewPanel({
  edges,
  nodeLabels,
  fileId,
  onConfirm,
  onReject,
  highlightKey = null,
  onHoverEdge,
  rejectedKeys = {},
  conceptTerms,
  proposedRelations,
  onConfirmTerm,
  onConfirmAllTerms,
  onExtractRelations,
  isExtracting = false,
}: EdgeReviewPanelProps) {
  // Rejected group collapsed by default
  const [showRejected, setShowRejected] = useState(false);
  const itemRefs = useRef<Record<string, HTMLLIElement | null>>({});

  const confirmedTermCount = useMemo(
    () => (conceptTerms ?? []).filter(t => t.confirmed).length,
    [conceptTerms]
  );
  const canExtract = confirmedTermCount >= 2;

  // Scroll to & flash highlighted entry (canvas -> panel linking)
  useEffect(() => {
    if (!highlightKey) return;
    const el = itemRefs.current[highlightKey];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('edge-review-flash');
      const timer = setTimeout(() => el.classList.remove('edge-review-flash'), 1600);
      return () => clearTimeout(timer);
    }
  }, [highlightKey]);

  const grouped = useMemo(() => {
    const buckets: Record<EdgeReviewStatus, GraphEdge[]> = { pending: [], confirmed: [], rejected: [] };
    edges.forEach(edge => {
      buckets[classifyEdge(edge, rejectedKeys)].push(edge);
    });
    return buckets;
  }, [edges, rejectedKeys]);

  /** T-D: concept term confirmation group (rendered above edge list) */
  const renderConceptGroup = () => {
    if (!conceptTerms || conceptTerms.length === 0) return null;

    return (
      <section className="mb-4" data-testid="concept-term-group">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-medium text-stardust-300">
            概念词（已确认 {confirmedTermCount}/{conceptTerms.length}）
          </div>
          <button
            type="button"
            data-testid="confirm-all-terms"
            onClick={() => onConfirmAllTerms?.()}
            disabled={confirmedTermCount === conceptTerms.length || isExtracting}
            className="px-2 py-0.5 rounded bg-nebula-500/80 hover:bg-nebula-400 text-white text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            全部确认
          </button>
        </div>

        <ul className="space-y-1 mb-2">
          {conceptTerms.map(ct => (
            <li
              key={ct.term}
              data-testid="concept-term-row"
              className="flex items-center gap-2 px-2 py-1.5 rounded bg-space-900/70"
            >
              <span className="text-sm text-gray-200 truncate flex-1">{ct.term}</span>
              <span className="text-void-400 text-[10px] truncate max-w-[80px]" title={ct.field_key}>
                {ct.field_key}
              </span>
              {ct.confirmed ? (
                <span
                  data-testid="term-confirmed-badge"
                  className="px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 text-xs whitespace-nowrap"
                >
                  ✓ 已确认
                </span>
              ) : (
                <button
                  type="button"
                  aria-label={`确认概念词 ${ct.term}`}
                  onClick={() => onConfirmTerm?.(ct.term)}
                  className="px-2 py-0.5 rounded bg-emerald-700/70 hover:bg-emerald-600 text-white text-xs transition-colors"
                >
                  ✓确认
                </button>
              )}
            </li>
          ))}
        </ul>

        <button
          type="button"
          data-testid="extract-relations"
          onClick={() => onExtractRelations?.()}
          disabled={!canExtract || isExtracting}
          title={canExtract ? undefined : '确认至少 2 个概念词'}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-nebula-500 hover:bg-nebula-400 text-white text-sm font-medium transition-colors disabled:bg-void-800 disabled:text-void-400 disabled:cursor-not-allowed"
        >
          {isExtracting && (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          {isExtracting ? '提取中...' : '提取概念关系'}
          {!canExtract && !isExtracting && (
            <span className="text-xs font-normal">（确认至少 2 个概念词）</span>
          )}
        </button>
      </section>
    );
  };

  if (edges.length === 0) {
    return (
      <aside
        className="w-[340px] shrink-0 h-full overflow-y-auto bg-space-900/60 border-l border-white/10 p-4"
        data-testid="edge-review-panel"
      >
        <h3 className="text-stardust-300 text-sm font-medium mb-3">概念边审核</h3>
        {renderConceptGroup()}
        <p className="text-void-400 text-sm leading-relaxed">
          暂无概念边——定稿后 AI 将从你的设定中提取概念关联网
        </p>
      </aside>
    );
  }

  const renderEdgeItem = (edge: GraphEdge, status: EdgeReviewStatus) => {
    const key = getEdgeKey(edge);
    const badge = tierBadge(edge);
    const fromLabel = nodeLabels[edge.from_node_id] || edge.from_node_id;
    const toLabel = nodeLabels[edge.to_node_id] || edge.to_node_id;
    const isConfirmed = status === 'confirmed';
    const isRejected = status === 'rejected';

    return (
      <li
        key={key}
        ref={el => { itemRefs.current[key] = el; }}
        data-edge-key={key}
        onMouseEnter={() => onHoverEdge?.(key)}
        onMouseLeave={() => onHoverEdge?.(null)}
        className={`p-3 rounded-lg bg-space-900/70 transition-colors ${STATUS_GROUPS.find(g => g.status === status)?.borderClass} ${
          isConfirmed ? 'bg-emerald-950/40' : ''
        } ${isRejected ? 'opacity-70' : ''}`}
      >
        <div className="flex items-start gap-2">
          <span className={badge.className} title={badge.title}>{badge.symbol}</span>
          <div className="flex-1 min-w-0">
            <div className={`text-sm truncate ${isConfirmed ? 'text-white font-bold' : 'text-gray-200'}`}>
              <span className={isConfirmed ? 'font-bold' : ''}>{fromLabel}</span>
              <span className="text-void-400 mx-1">→</span>
              <span className="text-void-300 text-xs">[{edge.relation || edge.visual_description}]</span>
              <span className={`ml-1 ${isConfirmed ? 'font-bold' : ''}`}>{toLabel}</span>
            </div>
            <div className="text-void-400 text-xs mt-1 line-clamp-2">{edge.visual_description}</div>
            {status === 'pending' && isNewRelationEdge(edge, proposedRelations) && (
              <span
                data-testid="new-relation-badge"
                className="inline-block mt-1 px-2 py-0.5 rounded border border-amber-400/70 text-amber-300 text-[10px] whitespace-nowrap"
              >
                新关系
              </span>
            )}
          </div>
          <div className="shrink-0">
            {status === 'pending' && (
              <div className="flex gap-1">
                <button
                  type="button"
                  aria-label={`确认 ${key}`}
                  onClick={() => onConfirm(key)}
                  className="px-2 py-1 rounded bg-emerald-700/70 hover:bg-emerald-600 text-white text-xs transition-colors"
                >
                  ✓
                </button>
                <button
                  type="button"
                  aria-label={`拒绝 ${key}`}
                  onClick={() => onReject(key)}
                  className="px-2 py-1 rounded bg-red-800/70 hover:bg-red-700 text-white text-xs transition-colors"
                >
                  ✗
                </button>
              </div>
            )}
            {isConfirmed && (
              <span className="px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 text-xs whitespace-nowrap">
                已确认
              </span>
            )}
            {isRejected && (
              <span className="px-2 py-0.5 rounded bg-gray-800/60 border border-gray-600/40 text-gray-400 text-xs whitespace-nowrap">
                已拒绝
              </span>
            )}
          </div>
        </div>
      </li>
    );
  };

  return (
    <aside
      className="w-[340px] shrink-0 h-full overflow-y-auto bg-space-900/60 border-l border-white/10 p-4"
      data-testid="edge-review-panel"
      data-file-id={fileId}
    >
      <h3 className="text-stardust-300 text-sm font-medium mb-3">概念边审核</h3>
      {renderConceptGroup()}
      <ul className="space-y-2">
        {STATUS_GROUPS.map(group => {
          const items = grouped[group.status];
          if (group.status === 'rejected') {
            if (items.length === 0) return null;
            return items.length > 0 && !showRejected ? (
              <li key={group.status}>
                <button
                  type="button"
                  onClick={() => setShowRejected(true)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-space-900/70 border-l-4 border-gray-600 text-left"
                >
                  <span className="text-gray-400 text-sm font-medium">已拒绝 ({items.length})</span>
                  <span className="text-void-400 text-xs">▶ 展开</span>
                </button>
              </li>
            ) : (
              <li key={group.status} className="space-y-2">
                <button
                  type="button"
                  onClick={() => setShowRejected(false)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-space-900/70 border-l-4 border-gray-600 text-left"
                >
                  <span className="text-gray-400 text-sm font-medium">已拒绝 ({items.length})</span>
                  <span className="text-void-400 text-xs">▼ 收起</span>
                </button>
                {items.map(edge => renderEdgeItem(edge, group.status))}
              </li>
            );
          }
          if (items.length === 0) return null;
          return (
            <li key={group.status} data-testid={`group-${group.status}`} className="space-y-2 list-none">
              <div className={`text-xs font-medium ${group.textClass}`}>
                {group.title} ({items.length})
              </div>
              {items.map(edge => renderEdgeItem(edge, group.status))}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
