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
import { WorldMap } from './WorldMap';
import { RackPanel } from './RackPanel';
import { EdgeReviewPanel } from './EdgeReviewPanel';
import type { KnowledgeGraph, GraphEdge } from '../../types/graph';
import type { ConceptTerm, ProposedRelation, WarningLedgerEntry } from '../../types/a1';
import type { OpenQuestionRecord } from '../../pages/a1/A1Workspace';
import { relationLabel, translateRelationInProse } from '../../labels/relationLabel';
import { draftStaleBarLabel } from '../../labels/draftBadge';

interface A1GraphSectionProps {
  fileId: string;
  returnToChat: () => void;
  version?: number;
  isStale?: boolean;
  openQuestions?: OpenQuestionRecord[];
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

/** J3: Chinese label for each ledger source channel. */
function ledgerSourceLabel(source: string): string {
  switch (source) {
    case 'assemble': return '组装';
    case 'finalize': return '定稿';
    case 'graphify': return '图谱化';
    case 'dead_edges': return '失效边';
    case 'upload': return '上传';
    default: return source;
  }
}

/** Fullscreen shell (T-C): absolutely fills its positioned parent — the
 *  workspace stacks it BELOW the title bar and tab nav (no overlap). */
function FullscreenShell({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 z-40 flex flex-col bg-space-950" data-testid="a1-graph-fullscreen">
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
  // P0: 只把 pending/asked 算作「待问」；answered/skipped 不显示也不计数
  const pendingOpenQuestions = useMemo(
    () => openQuestions.filter((q) => q.status === 'pending' || q.status === 'asked'),
    [openQuestions]
  );
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [lastGraph, setLastGraph] = useState<KnowledgeGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefinalizing, setIsRefinalizing] = useState(false);
  const [showRejectedList, setShowRejectedList] = useState(false);
  // Refinalize freshness: parent props (version/isStale) may arrive late
  // (graphCode fetched after mount) or only refresh on remount. A local
  // override set from the finalize response wins over the possibly-stale
  // prop until the next mount.
  const [versionOverride, setVersionOverride] = useState<number | null>(null);

  // T-D: two-phase concept flow state
  const [conceptTerms, setConceptTerms] = useState<ConceptTerm[]>([]);
  const [proposedRelations, setProposedRelations] = useState<ProposedRelation[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);

  // T16: degradation warnings from finalize (graphify degradation report)
  const [finalizeWarnings, setFinalizeWarnings] = useState<string[]>([]);
  const [showWarningsPopover, setShowWarningsPopover] = useState(false);
  // J3: structured warning ledger (four-channel merged view) from GET /api/a1/file/{id}
  const [warningsLedger, setWarningsLedger] = useState<WarningLedgerEntry[]>([]);

  // J3: split ledger by severity — warn entries drive the prominent badge,
  // info entries render weakened below them in the popover.
  const warnLedgerEntries = useMemo(() => warningsLedger.filter((e) => e.level === 'warn'), [warningsLedger]);
  const infoLedgerEntries = useMemo(() => warningsLedger.filter((e) => e.level !== 'warn'), [warningsLedger]);
  // Legacy fallback: old records only carry finalize_warnings (no ledger yet).
  const showLegacyFinalizeBadge = warningsLedger.length === 0 && finalizeWarnings.length > 0;
  // F2: dead edges from get_file response, surfaced in EdgeReviewPanel
  const [deadEdges, setDeadEdges] = useState<DeadEdge[]>([]);

  // Fullscreen layout state (T-C)
  const [viewMode, setViewMode] = useState<'tree' | 'concept' | 'worldmap'>('tree');
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

  const loadGraph = useCallback(async (attempt = 0): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchJson<KnowledgeGraph>(`/api/a1/file/${fileId}/graph`);
      setGraph(data);
      setLastGraph(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('pending_finalize');
      } else if (attempt === 0 && !(err instanceof ApiError)) {
        // Transient network failure (backend restart window / fetch abort):
        // one silent retry beats dumping the user onto an error screen.
        await new Promise((r) => setTimeout(r, 800));
        await loadGraph(1);
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

  // 波次三 T5：灵感架存量（material_pool）——活地图 tab 下 RackPanel 消费；
  // 安家入口走既有 /api/a1/chat 投递通道（后端批D 投递/回收机制，session_id 来自 file 端点）
  const [rackPool, setRackPool] = useState<{ text?: string; home?: string }[]>([]);
  const [rackSessionId, setRackSessionId] = useState<string | null>(null);
  const loadRack = useCallback(() => {
    fetchJson<{ material_pool?: { text?: string; home?: string }[]; session_id?: string }>(
      `/api/a1/file/${fileId}`
    )
      .then((file) => {
        setRackPool(file.material_pool ?? []);
        if (file.session_id) setRackSessionId(file.session_id);
      })
      .catch(() => {
        // fail-silent：灵感架非关键数据
      });
  }, [fileId]);
  useEffect(() => {
    loadRack();
  }, [loadRack]);
  // 安家操作：把灵感架条目作为投递消息发往既有 chat 端点，随后刷新存量（fail-silent）
  const stowRackItem = useCallback(
    (item: { text?: string; home?: string }) => {
      if (!rackSessionId) return;
      fetchJson<Record<string, unknown>>(`/api/a1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: rackSessionId,
          message: `把「${item.text ?? '这个想法'}」安家到${item.home ? `「${item.home}」` : '合适的模块'}`,
        }),
      })
        .then(() => loadRack())
        .catch(() => {
          // fail-silent：安家失败不阻塞图谱页
        });
    },
    [rackSessionId, loadRack]
  );

  // T-D: fetch file record for concept_terms / proposed_relations (resident fields)
  const loadFileTerms = useCallback(async () => {
    try {
      const file = await fetchJson<{
        concept_terms?: ConceptTerm[];
        proposed_relations?: ProposedRelation[];
        finalize_warnings?: string[];
        dead_edges?: DeadEdge[];
        warnings?: WarningLedgerEntry[];
      }>(`/api/a1/file/${fileId}`);
      setConceptTerms(file.concept_terms ?? []);
      setProposedRelations(file.proposed_relations ?? []);
      setFinalizeWarnings(file.finalize_warnings ?? []);
      setDeadEdges(file.dead_edges ?? []);
      setWarningsLedger(file.warnings ?? []);
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
      // Finalize is long-running (real LLM, server-side retry worst case
      // ~2x GRAPHIFY_TIMEOUT) — must outlive the 30s client default that
      // otherwise aborts mid-finalize (AbortError -> dead error screen).
      const res = await fetchJson<{ graph_code?: string }>(
        `/api/a1/file/${fileId}/finalize`,
        { method: 'POST', timeoutMs: 180_000 }
      );
      // Local freshness: parent props (version/isStale) refresh on remount;
      // derive the new version from the finalize response when present.
      const parsed = res.graph_code ? (res.graph_code.match(/-v(\d+)$/)?.[1] ? parseInt(res.graph_code.match(/-v(\d+)$/)[1], 10) : version + 1) : version + 1;
      setVersionOverride(Number.isFinite(parsed) ? parsed : version + 1);
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

  /** Confirm/reject failure surfaced in the panel — a dead button must never
   *  be silent (stale backend without the v0.5 endpoint fix 404s silently). */
  const [panelActionError, setPanelActionError] = useState<string | null>(null);

  const describeEdgeActionError = (err: unknown): string => {
    if (err instanceof ApiError && err.status === 404) {
      return '该边不存在或后端仍是旧版本——请重启后端进程后重试';
    }
    // Legacy wrappers throw plain Error('HTTP <status>') without a status
    // field — parse the message so 404 still gets the actionable copy.
    if (err instanceof Error && /HTTP 404/.test(err.message)) {
      return '该边不存在或后端仍是旧版本——请重启后端进程后重试';
    }
    if (err instanceof Error && /HTTP 5\d\d/.test(err.message)) {
      return `服务端错误（${err.message}）——请把此信息反馈给开发`;
    }
    if (err instanceof Error && err.name === 'AbortError') {
      return '请求超时';
    }
    return '网络错误——后端可能未启动，请启动后端后重试';
  };

  /** Confirm a concept edge from the review panel (slash-separated key). */
  const handlePanelConfirm = useCallback(async (edgeKey: string) => {
    try {
      setPanelActionError(null);
      await confirmEdge(fileId, edgeKey);
      await loadGraph();
    } catch (err) {
      console.error('Failed to confirm edge:', err);
      setPanelActionError(`确认失败（${describeEdgeActionError(err)}）`);
    }
  }, [fileId, loadGraph]);

  /** Reject a concept edge from the review panel. */
  const handlePanelReject = useCallback(async (edgeKey: string) => {
    try {
      setPanelActionError(null);
      await rejectEdge(fileId, edgeKey);
      await loadGraph();
    } catch (err) {
      console.error('Failed to reject edge:', err);
      setPanelActionError(`拒绝失败（${describeEdgeActionError(err)}）`);
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
              <div><span className="text-stardust-300">交互：</span>点击节点查看内容 · 搜索定位 · 交叉引用跳转（边类型见图内右下图例）</div>
            </div>
          </div>
        </div>
      </FullscreenShell>
    );
  }

  if (error && !lastGraph && !graph) {
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

  if (!graph) {
    // Initial load (no error, no graph yet) — spinner shell
    return (
      <FullscreenShell>
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
            <p className="text-stardust-300">加载图谱中...</p>
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
          <button
            onClick={() => setViewMode('worldmap')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'worldmap'
                ? 'bg-nebula-500 text-white'
                : 'bg-void-800 text-void-400 hover:bg-void-700'
            }`}
          >
            活地图
          </button>
        </div>

        {/* Right: stats + panel toggle */}
        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-3">
            {!isStale || versionOverride !== null ? (
              <span className="px-2 py-0.5 rounded bg-cosmos-success/10 border border-cosmos-success/30 text-cosmos-success text-xs whitespace-nowrap">
                已定稿 v{versionOverride ?? version} ✓
              </span>
            ) : null}
            {/* Always-available re-finalize: the answer -> refinalize loop
                must work for FINALIZED files too, not just stale drafts. */}
            <button
              onClick={handleRefinalize}
              disabled={isRefinalizing}
              className="px-2 py-0.5 rounded bg-cosmos-warning/10 border border-cosmos-warning/40 text-cosmos-warning text-xs whitespace-nowrap hover:bg-cosmos-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="refinalize-button"
              title="重新调用图谱化，纳入新回答/待问转正证据"
            >
              {isRefinalizing ? '定稿中…' : '↻ 重新定稿'}
            </button>
            <span className="text-amber-400">待确认 <b>{stats.pending}</b></span>
            <span className="text-emerald-400">已确认 <b>{stats.confirmed}</b></span>
            <span className="text-blue-400">待问 <b>{pendingOpenQuestions.length}</b></span>
            {/* T16/J3: degradation badge — structured ledger takes precedence;
                legacy finalizeWarnings badge only shown as fallback for old data */}
            {warningsLedger.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowWarningsPopover(v => !v)}
                  className={
                    warnLedgerEntries.length > 0
                      ? 'px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/50 text-amber-400 text-xs whitespace-nowrap hover:bg-amber-500/25 transition-colors'
                      : 'px-2 py-0.5 rounded bg-void-800/60 border border-white/15 text-void-300 text-xs whitespace-nowrap hover:bg-void-700/60 transition-colors'
                  }
                  data-testid="degradation-badge"
                >
                  {warnLedgerEntries.length > 0
                    ? <>⚠ 警告 {warnLedgerEntries.length} 项</>
                    : <>提示 {infoLedgerEntries.length} 项</>}
                </button>
                {showWarningsPopover && (
                  <div
                    className="absolute right-0 top-full mt-2 z-20 w-96 max-h-80 overflow-y-auto glass-panel p-4 bg-space-800/95 border-amber-500/30 text-left"
                    data-testid="degradation-popover"
                  >
                    <h3 className="text-amber-400 text-sm font-medium mb-2">降级明细</h3>
                    {warnLedgerEntries.length > 0 && (
                      <>
                        <p className="text-amber-400 text-xs mb-1.5 font-medium">警告</p>
                        <ul className="space-y-1.5 mb-3">
                          {warnLedgerEntries.map((e, i) => (
                            <li key={`warn-${i}`} className="flex items-start gap-2 text-xs">
                              <span className="text-amber-500 mt-0.5">•</span>
                              <span className="shrink-0 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400">
                                {ledgerSourceLabel(e.source)}
                              </span>
                              <span className="text-gray-200 break-all">
                                {translateRelationInProse(e.detail).replace(/endpoint_missing/g, '端点缺失')}
                                {e.count > 1 && <span className="text-amber-500"> ×{e.count}</span>}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                    {infoLedgerEntries.length > 0 && (
                      <>
                        <p className="text-void-300 text-xs mb-1.5 font-medium">提示</p>
                        <ul className="space-y-1.5">
                          {infoLedgerEntries.map((e, i) => (
                            <li key={`info-${i}`} className="flex items-start gap-2 text-xs opacity-70">
                              <span className="text-void-300 mt-0.5">•</span>
                              <span className="shrink-0 px-1.5 py-0.5 rounded bg-void-800 border border-white/15 text-void-300">
                                {ledgerSourceLabel(e.source)}
                              </span>
                              <span className="text-gray-400 break-all">
                                {translateRelationInProse(e.detail).replace(/endpoint_missing/g, '端点缺失')}
                                {e.count > 1 && <span> ×{e.count}</span>}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
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
            {showLegacyFinalizeBadge && (
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

      {/* ---- Load-failure banner (graph kept): transient GET /graph failure
            must not wipe the working canvas — show banner + retry instead ---- */}
      {error && (graph || lastGraph) && (
        <div
          className="shrink-0 flex items-center justify-between gap-4 px-4 py-2 bg-cosmos-error/10 border-b border-cosmos-error/30"
          data-testid="graph-load-error-banner"
        >
          <p className="text-sm text-cosmos-error">
            图谱刷新失败（网络或服务瞬时不可用）——当前展示上一版本图谱
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={loadGraph}
              className="px-3 py-1 rounded bg-cosmos-error/20 border border-cosmos-error/40 text-cosmos-error text-xs hover:bg-cosmos-error/30 transition-colors"
            >
              重试
            </button>
            <button
              onClick={() => setError(null)}
              className="px-3 py-1 rounded text-void-300 hover:text-stardust-300 text-xs transition-colors"
            >
              忽略
            </button>
          </div>
        </div>
      )}

      {/* ---- Stale banner (Mechanism 1) — hidden once locally refinalized ---- */}
      {isStale && versionOverride === null && (
        <div className="shrink-0 flex justify-center py-2 border-b border-white/5 bg-space-900/40">
          <button
            onClick={handleRefinalize}
            disabled={isRefinalizing}
            className="glass-panel px-4 py-2 bg-cosmos-warning/10 border-cosmos-warning/30 rounded-lg hover:bg-cosmos-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="text-cosmos-warning font-medium">
              ⚠ {draftStaleBarLabel(version)}
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
        <div className="flex-1 min-w-0 relative overflow-y-auto">
          {viewMode === 'worldmap' ? (
            <div className="p-4">
              <WorldMap graph={graph} />
              <RackPanel pool={rackPool} onStow={rackSessionId ? stowRackItem : undefined} />
            </div>
          ) : (
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
          )}

          {/* Pending questions overlay (P4, tree mode convenience) */}
          {viewMode === 'tree' && pendingOpenQuestions.length > 0 && (
            <div className="absolute bottom-4 left-4 z-10 w-80 glass-panel p-4 bg-space-800/80 border-white/10 max-h-[40%] overflow-y-auto">
              <h3 className="text-stardust-300 text-sm font-medium mb-2">
                待问 {pendingOpenQuestions.length}
              </h3>
              <ul className="space-y-2">
                {pendingOpenQuestions.map((q, index) => (
                  <li key={q.id || index} className="flex items-start gap-2">
                    <span className="text-nebula-400 mt-1">•</span>
                    <span className="text-gray-300 flex-1 text-xs">{translateRelationInProse(q.question)}</span>
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

          {/* Edge-type legend lives in the canvas (A1KnowledgeGraph bottom bar) —
              no duplicate overlay here (legend consolidation). */}
        </div>

        {/* Right review panel (concept mode only) */}
        {viewMode === 'concept' && panelOpen && (
          <EdgeReviewPanel
            edges={conceptEdges}
            nodeLabels={nodeLabels}
            fileId={fileId}
        onConfirm={handlePanelConfirm}
        onReject={handlePanelReject}
        actionError={panelActionError}
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
                    <div className="text-void-400 text-xs">{relationLabel(edge.relation)}</div>
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
