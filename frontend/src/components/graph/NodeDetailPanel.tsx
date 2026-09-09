/**
 * NodeDetailPanel — A1 knowledge-graph node detail overlay (graph "indexification").
 *
 * The canvas only indexes entries; this panel carries the full content:
 * - Per-kind detail body (L2 summary / L3 answer text / d: depth content / ids)
 * - Related-edge list (click → navigate to the peer node)
 * - Cross-reference auto-linking: other entry titles appearing in the body text
 *   render as clickable links (buildCrosslinks pure function below).
 */

import React, { useMemo } from 'react';
import type { KnowledgeGraph, GraphNode, GraphEdge } from '../../types/graph';

/** Depth-tree node id prefix (form `d:{anchor}:{title}`). */
export const isDepthId = (id: string): boolean => id.startsWith('d:');

/** Concept-term node id prefix (form `term:{word}`). */
export const isTermId = (id: string): boolean => id.startsWith('term:');

/**
 * Display title of a node (shared by panel header, search results,
 * related-edge peer names and crosslink terms):
 * d: → id title segment (`d:{anchor}:{title}` → everything after the 2nd colon);
 * L3 → field name (text before the first colon in description);
 * L2/L1 → module/background description; term → the term word; L0/cst → id.
 */
export const nodeTitle = (node: Pick<GraphNode, 'id' | 'level' | 'description'>): string => {
  if (isTermId(node.id)) return node.description;
  if (isDepthId(node.id)) {
    const title = node.id.split(':').slice(2).join(':').trim();
    return title || node.id;
  }
  if (node.level === 3) {
    const idx = node.description.indexOf(':');
    return idx > 0 ? node.description.slice(0, idx).trim() : node.description;
  }
  if (node.level === 1 || node.level === 2) return node.description;
  return node.id;
};

/** Human-readable node kind label (search result subtitle / panel badge). */
export const nodeKindLabel = (node: Pick<GraphNode, 'id' | 'level'>): string => {
  if (isTermId(node.id)) return '概念';
  if (isDepthId(node.id)) return '深度条目';
  if (node.level <= 0) return '约束';
  if (node.level === 1) return '背景';
  if (node.level === 2) return '模块';
  return '条目';
};

/** Parent module name for an L3/d: node (via tree edges); undefined when rootless. */
export const parentModuleName = (
  node: Pick<GraphNode, 'id'>,
  graph: Pick<KnowledgeGraph, 'nodes' | 'edges'>
): string | undefined => {
  const treeEdge = graph.edges.find(e => e.edge_type === 'tree' && e.to_node_id === node.id);
  if (!treeEdge) return undefined;
  const parent = graph.nodes[treeEdge.from_node_id];
  return parent ? nodeTitle(parent) : undefined;
};

// ---------------------------------------------------------------------------
// Cross-reference auto-linking
// ---------------------------------------------------------------------------

/** A linkable term: display text + target node id. */
export interface CrosslinkTerm {
  term: string;
  nodeId: string;
}

/** One segment of the split content: plain text or a crosslink. */
export interface CrosslinkSegment {
  text: string;
  /** Present → render as clickable crosslink to this node. */
  nodeId?: string;
}

const escapeRegExp = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Split `content` into segments, marking occurrences of other entries' titles
 * as crosslinks.
 * - Terms are matched longest-first (regex alternation order), case-sensitive
 *   global scan, regex-escaped.
 * - A term pointing at `selfId` is excluded (self-references are not links).
 */
export const buildCrosslinks = (
  content: string,
  terms: CrosslinkTerm[],
  selfId: string
): CrosslinkSegment[] => {
  if (!content) return [];
  const usable = terms.filter(t => t.term && t.term.length >= 2 && t.nodeId !== selfId);
  if (usable.length === 0) return [{ text: content }];

  // Longest first so a longer title wins over its own prefix.
  const sorted = [...usable].sort((a, b) => b.term.length - a.term.length);
  const nodeByTerm = new Map(sorted.map(t => [t.term, t.nodeId]));
  const re = new RegExp(`(${sorted.map(t => escapeRegExp(t.term)).join('|')})`, 'g');

  const segments: CrosslinkSegment[] = [];
  let last = 0;
  for (const m of content.matchAll(re)) {
    const idx = m.index ?? 0;
    if (idx > last) segments.push({ text: content.slice(last, idx) });
    segments.push({ text: m[0], nodeId: nodeByTerm.get(m[0]) });
    last = idx + m[0].length;
  }
  if (last < content.length) segments.push({ text: content.slice(last) });
  return segments;
};

/** Build the crosslink term table from every node of the graph. */
export const buildTermTable = (graph: KnowledgeGraph): CrosslinkTerm[] =>
  Object.values(graph.nodes)
    .map(n => ({ term: nodeTitle(n), nodeId: n.id }))
    .filter(t => t.term.length >= 2);

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface SearchHit {
  nodeId: string;
  title: string;
  kind: string;
  snippet: string;
}

const SNIPPET_RADIUS = 12;

/**
 * Pure search: match node title + description via case-insensitive `includes`.
 * Returns at most 10 hits with a ±12-char snippet around the first match.
 */
export const searchGraphNodes = (
  query: string,
  graph: Pick<KnowledgeGraph, 'nodes'>
): SearchHit[] => {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const hits: SearchHit[] = [];
  for (const node of Object.values(graph.nodes)) {
    const title = nodeTitle(node);
    const kind = nodeKindLabel(node);
    const haystack = `${title}\n${node.description}`.toLowerCase();
    if (!haystack.includes(q)) continue;

    // Snippet from the description when possible (fall back to the title).
    const source = node.description || title;
    const lower = source.toLowerCase();
    const at = lower.indexOf(q);
    let snippet: string;
    if (at === -1) {
      snippet = source.slice(0, SNIPPET_RADIUS * 2);
    } else {
      const start = Math.max(0, at - SNIPPET_RADIUS);
      const end = Math.min(source.length, at + q.length + SNIPPET_RADIUS);
      snippet = `${start > 0 ? '…' : ''}${source.slice(start, end)}${end < source.length ? '…' : ''}`;
    }
    hits.push({ nodeId: node.id, title, kind, snippet });
    if (hits.length >= 10) break;
  }
  return hits;
};

// ---------------------------------------------------------------------------
// Panel component
// ---------------------------------------------------------------------------

export interface NodeDetailPanelProps {
  node: GraphNode | null;
  graph: KnowledgeGraph;
  onClose?: () => void;
  /** Crosslink / related-edge click: parent centers the graph and switches the panel. */
  onNavigate?: (nodeId: string) => void;
}

/** Full body text whose occurrences of other titles become crosslinks. */
const bodyTextOf = (node: GraphNode): string => node.description;

const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ node, graph, onClose, onNavigate }) => {
  const terms = useMemo(() => buildTermTable(graph), [graph]);

  const relatedEdges: { edge: GraphEdge; peerId: string }[] = useMemo(() => {
    if (!node) return [];
    return graph.edges
      .filter(e => e.from_node_id === node.id || e.to_node_id === node.id)
      .map(e => ({
        edge: e,
        peerId: e.from_node_id === node.id ? e.to_node_id : e.from_node_id,
      }));
  }, [graph, node]);

  if (!node) return null;

  const title = nodeTitle(node);
  const kind = nodeKindLabel(node);
  const parent = parentModuleName(node, graph);
  const segments = buildCrosslinks(bodyTextOf(node), terms, node.id);

  const renderSegments = () =>
    segments.map((seg, i) =>
      seg.nodeId ? (
        <button
          key={i}
          type="button"
          data-testid="content-crosslink"
          onClick={() => onNavigate?.(seg.nodeId!)}
          className="text-left underline decoration-dotted underline-offset-2 hover:decoration-solid transition-colors"
          style={{ color: 'var(--color-stardust-400, #fbbf24)' }}
          title="跳转到该条目"
        >
          {seg.text}
        </button>
      ) : (
        <React.Fragment key={i}>{seg.text}</React.Fragment>
      )
    );

  const badgeFor = (e: GraphEdge) => {
    if (e.confirmed === true) {
      return <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-500/40">已确认</span>;
    }
    if (e.confidence === 'semantic' && e.confirmed === false) {
      return <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-300 border border-amber-500/40">待确认</span>;
    }
    return null;
  };

  return (
    <div
      data-testid="node-detail-panel"
      className="absolute top-0 right-0 h-full z-30 w-[340px] flex flex-col bg-void-900/95 border-l border-nebula-500/40 backdrop-blur-sm shadow-2xl"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-4 border-b border-void-700">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-nebula-400 mb-1">{kind}</div>
          <div className="text-sm font-medium text-white break-words" data-testid="node-detail-title">
            {title}
          </div>
        </div>
        <button
          type="button"
          data-testid="node-detail-close"
          onClick={onClose}
          className="text-void-400 hover:text-white transition-colors shrink-0"
          aria-label="关闭详情"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {/* Module extras */}
        {node.level === 2 && node.tier !== undefined && (
          <div className="text-xs text-void-400">
            层级：<span className="text-nebula-300">tier {node.tier}</span>
          </div>
        )}

        {/* Parent context */}
        {parent && (
          <div className="text-xs text-void-400">
            所属：<span className="text-void-300">{parent}</span>
          </div>
        )}

        {/* Full content with crosslinks */}
        <div>
          <div className="text-[10px] uppercase tracking-wider text-void-500 mb-1">
            {node.level === 3 ? '答案原文' : isDepthId(node.id) ? '条目内容' : '内容'}
          </div>
          <div className="text-void-200 leading-relaxed whitespace-pre-wrap break-words" data-testid="node-detail-body">
            {renderSegments()}
          </div>
        </div>

        {/* Related edges */}
        {relatedEdges.length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-void-500 mb-2">
              关联条目（{relatedEdges.length}）
            </div>
            <ul className="space-y-1.5" data-testid="node-detail-related-edges">
              {relatedEdges.map(({ edge, peerId }) => {
                const peer = graph.nodes[peerId];
                const rel = edge.relation || edge.visual_description;
                return (
                  <li key={`${edge.from_node_id}-${edge.to_node_id}-${rel}`}>
                    <button
                      type="button"
                      data-testid="node-detail-related-edge"
                      onClick={() => onNavigate?.(peerId)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded bg-void-800/70 border border-void-700 hover:border-nebula-400 transition-colors text-left"
                    >
                      <span className="text-xs text-nebula-300 shrink-0">{rel}</span>
                      <span className="text-xs text-white truncate flex-1">
                        {peer ? nodeTitle(peer) : peerId}
                      </span>
                      {badgeFor(edge)}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default NodeDetailPanel;
