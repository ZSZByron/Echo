/**
 * A1GraphSection Component
 *
 * Task T-C: Fullscreen knowledge graph layout (fixed inset-0 overlay).
 * Top toolbar (56px): back to chat / [行政树|概念网] tabs / stats bar.
 * Body: React Flow canvas (flex-1) + right EdgeReviewPanel (340px, collapsible).
 * Concept-net guide bar (first visit, localStorage-gated).
 */

import { useState, useCallback, useEffect, useMemo, type ReactNode } from 'react';
import { fetchJson, ApiError } from '../../api/client';
import { confirmEdge, rejectEdge, confirmConceptTerms, extractConceptRelations, discardDeadEdge, getDeadEdgeKey, type DeadEdge } from '../../api/a1';
import { A1KnowledgeGraph, conceptEdgeKey } from './A1KnowledgeGraph';
import { EdgeReviewPanel } from './EdgeReviewPanel';
import type { KnowledgeGraph, GraphEdge } from '../../types/graph';
import type { ConceptTerm, ProposedRelation } from '../../types/a1';

interface A1GraphSectionProps {
  fileId: string;
  returnToChat: () => void;
  version?: number;
  isStale?: boolean;
  openQuestions?: string[];
  rejectedEdges?: Record<string, { from_node_id: string; to_node_id: string; relation: string }>;
}

const CONCEPT_GUIDE_KEY = 'a1_concept_guide_seen';

/** T16: derive a Chinese domain label from the warning prefix ([entries]/[edges]/[constraint_fields]). */
function warningDomainLabel(w: string): string | null {
  if (w.startsWith('[entries]')) return '条目';
  if (w.startsWith('[edges]')) return '边';
  if (w.startsWith('[constraint_fields]')) return '约束';
  return null;
}

/** T16: strip the machine prefix so the popover shows clean Chinese text. */
function stripWarningPrefix(w: string): string {
  return w.replace(/^\[(entries|edges|constraint_fields)\]\s*/, '');
}

/** Fixed fullscreen overlay shell (T-C): covers the entire workspace viewport. */
function FullscreenShell({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex flex-col bg-space-950" data-testid="a1-graph-fullscreen">
      {children}
    </div>
  );
}

export function A1GraphSection({
  fileId,
  returnToChat,
  version = 1,
  isStale = false,
  openQuestions = [],
  rejectedEdges = {},
}: A1GraphSectionProps) {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [lastGraph, setLastGraph] = useState<KnowledgeGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefinalizing, setIsRefinalizing] = useState(false);
  const [showRejectedList, setShowRejectedList] = useState(false);

  // T-D: two-phase concept flow state
  const [conceptTerms, setConceptTerms] = useState<ConceptTerm[]>([]);
  const [proposedRelations, setProposedRelations] = useState<ProposedRelation[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);

  // T16: degradation warnings from finalize (graphify degradation report)
  const [finalizeWarnings, setFinalizeWarnings] = useState<string[]>([]);
  const [showWarningsPopover, setShowWarningsPopover] = useState(false);
  // F2: dead edges from get_file response, surfaced in EdgeReviewPanel
  const [deadEdges, setDeadEdges] = useState<DeadEdge[]>([]);

  // Fullscreen layout state (T-C)
  const [viewMode, setViewMode] = useState<'tree' | 'concept'>('tree');
  const [panelOpen, setPanelOpen] = useState(true);
  const [focusEdgeKey, setFocusEdgeKey] = useState<string | null>(null);
  const [hoverEdgeKey, setHoverEdgeKey] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  // Show guide on first concept-net visit
  useEffect(() => {
    if (viewMode === 'concept' && !localStorage.getItem(CONCEPT_GUIDE_KEY)) {
      setShowGuide(true);
    }
  }, [viewMode]);

  const dismissGuide = useCallback(() => {
    localStorage.setItem(CONCEPT_GUIDE_KEY, '1');
    setShowGuide(false);
  }, []);

  const loadGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchJson<KnowledgeGraph>(`/api/a1/file/${fileId}/graph`);
      setGraph(data);
      setLastGraph(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('pending_finalize');
      } else {
        console.error('Failed to load graph:', err);
        setError('Failed to load graph');
      }
    } finally {
      setIsLoading(false);
    }
  }, [fileId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // T-D: fetch file record for concept_terms / proposed_relations (resident fields)
  const loadFileTerms = useCallback(async () => {
    try {
      const file = await fetchJson<{
        concept_terms?: ConceptTerm[];
        proposed_relations?: ProposedRelation[];
        finalize_warnings?: string[];
        dead_edges?: DeadEdge[];
      }>(`/api/a1/file/${fileId}`);
      setConceptTerms(file.concept_terms ?? []);
      setProposedRelations(file.proposed_relations ?? []);
      setFinalizeWarnings(file.finalize_warnings ?? []);
      setDeadEdges(file.dead_edges ?? []);
    } catch (err) {
      console.error('Failed to load concept terms:', err);
    }
  }, [fileId]);

  useEffect(() => {
    loadFileTerms();
  }, [loadFileTerms]);

  /** T-D: confirm one concept term into dictionary. */
  const handleConfirmTerm = useCallback(async (term: string) => {
    try {
      const res = await confirmConceptTerms(fileId, [term]);
      setConceptTerms(res.concept_terms);
    } catch (err) {
      console.error('Failed to confirm term:', err);
    }
  }, [fileId]);

  /** T-D: confirm all concept terms at once. */
  const handleConfirmAllTerms = useCallback(async () => {
    try {
      const res = await confirmConceptTerms(fileId, 'all');
      setConceptTerms(res.concept_terms);
    } catch (err) {
      console.error('Failed to confirm all terms:', err);
    }
  }, [fileId]);

  /** T-D: LLM edge extraction (30-90s) then refresh graph + file fields. */
  const handleExtractRelations = useCallback(async () => {
    if (isExtracting) return;
    setIsExtracting(true);
    try {
      await extractConceptRelations(fileId);
      await Promise.all([loadGraph(), loadFileTerms()]);
    } catch (err) {
      console.error('Failed to extract concept relations:', err);
    } finally {
      setIsExtracting(false);
    }
  }, [fileId, isExtracting, loadGraph, loadFileTerms]);

  const handleRefinalize = async () => {
    if (!fileId || isRefinalizing) return;

    setIsRefinalizing(true);
    setError(null);

    try {
      await fetchJson(`/api/a1/file/${fileId}/finalize`, { method: 'POST' });
      // Reload graph after successful finalize
      await loadGraph();
    } catch (err) {
      console.error('Failed to refinalize:', err);
      setError('Failed to refinalize. Please try again.');
    } finally {
      setIsRefinalizing(false);
    }
  };

  const handleRestoreEdge = async (edgeKey: string) => {
    try {
      await confirmEdge(fileId, edgeKey);
      // Reload graph after restore
      await loadGraph();
    } catch (err) {
      console.error('Failed to restore edge:', err);
      setError('Failed to restore edge. Please try again.');
    }
  };

  /** Confirm a concept edge from the review panel (slash-separated key). */
  const handlePanelConfirm = useCallback(async (edgeKey: string) => {
    try {
      await confirmEdge(fileId, edgeKey);
      await loadGraph();
    } catch (err) {
      console.error('Failed to confirm edge:', err);
    }
  }, [fileId, loadGraph]);

  /** Reject a concept edge from the review panel. */
  const handlePanelReject = useCallback(async (edgeKey: string) => {
    try {
      await rejectEdge(fileId, edgeKey);
      await loadGraph();
    } catch (err) {
      console.error('Failed to reject edge:', err);
    }
  }, [fileId, loadGraph]);

  /** F2: discard a dead edge via reject endpoint, then drop it from local state. */
  const handleDiscardDeadEdge = useCallback(async (edge: DeadEdge) => {
    try {
      await discardDeadEdge(fileId, edge);
      setDeadEdges(prev => prev.filter(d => getDeadEdgeKey(d) !== getDeadEdgeKey(edge)));
    } catch (err) {
      console.error('Failed to discard dead edge:', err);
    }
  }, [fileId]);

  const handleGoAnswer = () => {
    localStorage.setItem('a1_return_intent', 'chat');
    returnToChat();
  };

  // Concept edges + stats derived from graph (T-C toolbar stats)
  const conceptEdges: GraphEdge[] = useMemo(
    () => (graph ? graph.edges.filter(e => e.confidence === 'semantic' || e.confidence === 'rule' || e.confidence === 'structure') : []),
    [graph]
  );
  const stats = useMemo(() => {
    const pending = conceptEdges.filter(e => e.confirmed === false && e.confidence === 'semantic').length;
    const confirmed = conceptEdges.filter(e => e.confirmed === true).length;
    return { pending, confirmed };
  }, [conceptEdges]);
  const nodeLabels = useMemo(() => {
    if (!graph) return {} as Record<string, string>;
    const map: Record<string, string> = {};
    Object.values(graph.nodes).forEach(n => { map[n.id] = n.description; });
    return map;
  }, [graph]);

  // ---- Fullscreen container (T-C): fixed overlay covering the workspace ----
  if (isLoading) {
    return (
      <FullscreenShell>
        {/* Top toolbar — back button must be reachable even during loading,
            otherwise the user is trapped in the fullscreen spinner. */}
        <div className="h-14 shrink-0 flex items-center px-4 border-b border-white/10 bg-space-900/70">
          <button
            onClick={returnToChat}
            className="px-3 py-1.5 rounded-md text-sm font-medium text-stardust-300 hover:bg-white/10 transition-colors"
          >
            ← 返回访谈
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-stardust-300">构建知识图谱中...</p>
          </div>
        </div>
      </FullscreenShell>
    );
  }

  if (error === 'pending_finalize') {
    return (
      <FullscreenShell>
        {/* Top toolbar */}
        <div className="h-14 shrink-0 flex items-center justify-between gap-4 px-4 border-b border-white/10 bg-space-900/70">
          <button
            onClick={returnToChat}
            className="px-3 py-1.5 rounded-md text-sm font-medium text-stardust-300 hover:bg-white/10 transition-colors"
          >
            ← 返回访谈
          </button>
          <span className="text-void-400 text-sm">知识图谱</span>
          <div className="w-24" />
        </div>

        <div className="flex-1 min-h-0 flex flex-col p-4 gap-4 overflow-y-auto">
          <div className="flex items-center justify-between">
            <button
              onClick={handleRefinalize}
              disabled={isRefinalizing}
              className="glass-panel px-4 py-2 bg-cosmos-warning/10 border-cosmos-warning/30 rounded-lg hover:bg-cosmos-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="text-cosmos-warning font-medium">
                ⚠ 设定已更新——点此重新定稿查看新图
              </span>
            </button>
          </div>

          {lastGraph && (
            <div className="flex-1 min-h-[50vh]">
              <A1KnowledgeGraph graph={lastGraph} isLoading={false} error={null} />
            </div>
          )}

          <div className="glass-panel p-4">
            <h3 className="text-stardust-300 text-sm font-medium mb-2">图例说明</h3>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-void-400 text-xs">
              <div><span className="text-stardust-300">节点层级：</span>约束 / 世界背景 / 模块 / 设定条目</div>
              <div><span className="text-stardust-300">边类型：</span>实线 = 层级包含 / 虚线 = 约束拓扑</div>
            </div>
          </div>
        </div>
      </FullscreenShell>
    );
  }

  if (error || !graph) {
    return (
      <FullscreenShell>
        {/* Top toolbar — back button must be reachable on error too. */}
        <div className="h-14 shrink-0 flex items-center px-4 border-b border-white/10 bg-space-900/70">
          <button
            onClick={returnToChat}
            className="px-3 py-1.5 rounded-md text-sm font-medium text-stardust-300 hover:bg-white/10 transition-colors"
          >
            ← 返回访谈
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="glass-panel p-8 bg-cosmos-error/10 border-cosmos-error/30 text-center">
            <p className="text-cosmos-error mb-4">{error || 'Failed to load graph'}</p>
            <button
              onClick={loadGraph}
              className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-colors"
            >
              重试
            </button>
          </div>
        </div>
      </FullscreenShell>
    );
  }

  return (
    <FullscreenShell>
      {/* ---- Top toolbar (56px) ---- */}
      <div className="h-14 shrink-0 flex items-center justify-between gap-4 px-4 border-b border-white/10 bg-space-900/70">
        {/* Left: back */}
        <button
          onClick={returnToChat}
          className="px-3 py-1.5 rounded-md text-sm font-medium text-stardust-300 hover:bg-white/10 transition-colors"
        >
          ← 返回访谈
        </button>

        {/* Center: view tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('tree')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'tree'
                ? 'bg-nebula-500 text-white'
                : 'bg-void-800 text-void-400 hover:bg-void-700'
            }`}
          >
            行政树
          </button>
          <button
            onClick={() => setViewMode('concept')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'concept'
                ? 'bg-nebula-500 text-white'
                : 'bg-void-800 text-void-400 hover:bg-void-700'
            }`}
          >
            概念网
          </button>
        </div>

        {/* Right: stats + panel toggle */}
        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-3">
            {!isStale && (
              <span className="px-2 py-0.5 rounded bg-cosmos-success/10 border border-cosmos-success/30 text-cosmos-success text-xs whitespace-nowrap">
                已定稿 v{version} ✓
              </span>
            )}
            <span className="text-amber-400">待确认 <b>{stats.pending}</b></span>
            <span className="text-emerald-400">已确认 <b>{stats.confirmed}</b></span>
            <span className="text-blue-400">待问 <b>{openQuestions.length}</b></span>
            {/* T16: degradation badge — only when finalize produced warnings */}
            {finalizeWarnings.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowWarningsPopover(v => !v)}
                  className="px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 text-amber-400 text-xs whitespace-nowrap hover:bg-amber-500/25 transition-colors"
                  data-testid="degradation-badge"
                >
                  本轮降级：{finalizeWarnings.length} 项
                </button>
                {showWarningsPopover && (
                  <div
                    className="absolute right-0 top-full mt-2 z-20 w-96 max-h-80 overflow-y-auto glass-panel p-4 bg-space-800/95 border-amber-500/30 text-left"
                    data-testid="degradation-popover"
                  >
                    <h3 className="text-amber-400 text-sm font-medium mb-2">降级明细</h3>
                    <ul className="space-y-1.5">
                      {finalizeWarnings.map((w, i) => {
                        const domain = warningDomainLabel(w);
                        return (
                          <li key={i} className="flex items-start gap-2 text-xs">
                            <span className="text-amber-500 mt-0.5">•</span>
                            {domain && (
                              <span className="shrink-0 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400">
                                {domain}
                              </span>
                            )}
                            <span className="text-gray-300 break-all">{stripWarningPrefix(w)}</span>
                          </li>
                        );
                      })}
                    </ul>
                    <button
                      onClick={() => setShowWarningsPopover(false)}
                      className="mt-3 text-xs text-void-300 hover:text-stardust-300 transition-colors"
                    >
                      收起
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
          {viewMode === 'concept' && (
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className="px-2 py-1 rounded border border-white/15 text-void-300 hover:bg-white/10 text-xs transition-colors"
            >
              {panelOpen ? '隐藏清单 ▶' : '显示清单 ◀'}
            </button>
          )}
        </div>
      </div>

      {/* ---- Stale banner (Mechanism 1) ---- */}
      {isStale && (
        <div className="shrink-0 flex justify-center py-2 border-b border-white/5 bg-space-900/40">
          <button
            onClick={handleRefinalize}
            disabled={isRefinalizing}
            className="glass-panel px-4 py-2 bg-cosmos-warning/10 border-cosmos-warning/30 rounded-lg hover:bg-cosmos-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="text-cosmos-warning font-medium">
              ⚠ 设定已更新——点此重新定稿查看新图（当前 v{version}）
            </span>
          </button>
        </div>
      )}

      {/* ---- Concept-net guide bar (first visit) ---- */}
      {viewMode === 'concept' && showGuide && (
        <div
          className="shrink-0 flex items-center justify-between gap-4 px-4 py-2 bg-nebula-500/10 border-b border-nebula-500/30"
          data-testid="concept-guide-bar"
        >
          <p className="text-sm text-gray-200">
            这是从你的设定中提取的<b className="text-stardust-300">概念关联网</b>——节点是你设定中的概念词，连线表示概念间的关系。请在右侧清单确认 AI 推断的关系。
          </p>
          <button
            onClick={dismissGuide}
            className="shrink-0 px-3 py-1 rounded bg-nebula-500 hover:bg-nebula-400 text-white text-sm transition-colors"
          >
            知道了
          </button>
        </div>
      )}

      {/* ---- Body: canvas + review panel ---- */}
      <div className="flex-1 min-h-0 flex">
        {/* Canvas */}
        <div className="flex-1 min-w-0 relative">
          <A1KnowledgeGraph
            graph={graph}
            isLoading={false}
            error={null}
            fileId={fileId}
            onRefresh={loadGraph}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            onEdgeFocus={setFocusEdgeKey}
            focusEdgeKey={focusEdgeKey}
            hoverEdgeKey={hoverEdgeKey}
            conceptTerms={conceptTerms}
          />

          {/* Pending questions overlay (P4, tree mode convenience) */}
          {viewMode === 'tree' && openQuestions.length > 0 && (
            <div className="absolute bottom-4 left-4 z-10 w-80 glass-panel p-4 bg-space-800/80 border-white/10 max-h-[40%] overflow-y-auto">
              <h3 className="text-stardust-300 text-sm font-medium mb-2">
                待问 {openQuestions.length}
              </h3>
              <ul className="space-y-2">
                {openQuestions.map((question, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-nebula-400 mt-1">•</span>
                    <span className="text-gray-300 flex-1 text-xs">{question}</span>
                    <button
                      onClick={handleGoAnswer}
                      className="text-stardust-400 hover:text-stardust-300 text-xs font-medium transition-colors"
                    >
                      去回答 →
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Legend */}
          <div className="absolute bottom-4 right-4 z-10 glass-panel px-4 py-2">
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-void-400 text-xs">
              <div><span className="text-emerald-400">★</span> 铁律推断</div>
              <div><span className="text-amber-400">◆</span> 联想</div>
              <div><span className="text-gray-400">◇</span> 结构拆解</div>
            </div>
          </div>
        </div>

        {/* Right review panel (concept mode only) */}
        {viewMode === 'concept' && panelOpen && (
          <EdgeReviewPanel
            edges={conceptEdges}
            nodeLabels={nodeLabels}
            fileId={fileId}
            onConfirm={handlePanelConfirm}
            onReject={handlePanelReject}
            highlightKey={focusEdgeKey}
            onHoverEdge={setHoverEdgeKey}
            rejectedKeys={rejectedEdges}
            conceptTerms={conceptTerms}
            proposedRelations={proposedRelations}
            onConfirmTerm={handleConfirmTerm}
            onConfirmAllTerms={handleConfirmAllTerms}
            onExtractRelations={handleExtractRelations}
            isExtracting={isExtracting}
            deadEdges={deadEdges}
            onDiscardDeadEdge={handleDiscardDeadEdge}
          />
        )}
      </div>

      {/* ---- Rejected edges restore list (Mechanism 4, tree mode) ---- */}
      {viewMode === 'tree' && Object.keys(rejectedEdges).length > 0 && (
        <div className="absolute bottom-20 left-4 z-10 w-96 glass-panel p-4 bg-space-800/80 border-white/10 max-h-[40%] overflow-y-auto">
          <button
            onClick={() => setShowRejectedList(!showRejectedList)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-stardust-300 text-sm font-medium">
              已拒绝清单 ({Object.keys(rejectedEdges).length} 条已拒绝边)
            </h3>
            <span className="text-void-400">{showRejectedList ? '▼' : '▶'}</span>
          </button>

          {showRejectedList && (
            <ul className="mt-3 space-y-2">
              {Object.entries(rejectedEdges).map(([edgeKey, edge]) => (
                <li key={edgeKey} className="flex items-center gap-3 p-2 bg-space-900/50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <div className="text-gray-300 text-xs truncate">
                      {edge.from_node_id} → {edge.to_node_id}
                    </div>
                    <div className="text-void-400 text-xs">{edge.relation}</div>
                  </div>
                  <button
                    onClick={() => handleRestoreEdge(edgeKey)}
                    className="bg-stardust-400 text-space-950 px-2 py-1 rounded text-xs font-medium hover:bg-stardust-300 transition-colors"
                  >
                    恢复
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </FullscreenShell>
  );
}

// Re-export for consumers that imported the key helper from A1GraphSection
export { conceptEdgeKey };
