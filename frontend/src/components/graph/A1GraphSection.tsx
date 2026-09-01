/**
 * A1GraphSection Component
 *
 * Displays the knowledge graph with status badge, rejected list, and pending questions.
 * Task 10: Extended from A1Workspace with new features per design doc §6.7 mechanisms 1/4/6.
 */

import { useState, useCallback, useEffect } from 'react';
import { fetchJson, ApiError } from '../../api/client';
import { confirmEdge } from '../../api/a1';
import { A1KnowledgeGraph } from './A1KnowledgeGraph';
import type { KnowledgeGraph } from '../../types/graph';

interface A1GraphSectionProps {
  fileId: string;
  returnToChat: () => void;
  version?: number;
  isStale?: boolean;
  openQuestions?: string[];
  rejectedEdges?: Record<string, { from_node_id: string; to_node_id: string; relation: string }>;
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

  const handleGoAnswer = () => {
    localStorage.setItem('a1_return_intent', 'chat');
    returnToChat();
  };

  if (isLoading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-stardust-300">构建知识图谱中...</p>
        </div>
      </div>
    );
  }

  if (error === 'pending_finalize') {
    return (
      <div className="space-y-6">
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
          <div className="h-[70vh]">
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
    );
  }

  if (error || !graph) {
    return (
      <div className="glass-panel p-8 bg-cosmos-error/10 border-cosmos-error/30 text-center">
        <p className="text-cosmos-error mb-4">{error || 'Failed to load graph'}</p>
        <button
          onClick={loadGraph}
          className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-colors"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Badge (Mechanism 1) */}
      <div className="flex items-center justify-between">
        {isStale ? (
          <button
            onClick={handleRefinalize}
            disabled={isRefinalizing}
            className="glass-panel px-4 py-2 bg-cosmos-warning/10 border-cosmos-warning/30 rounded-lg hover:bg-cosmos-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="text-cosmos-warning font-medium">
              ⚠ 设定已更新——点此重新定稿查看新图
            </span>
          </button>
        ) : (
          <div className="glass-panel px-4 py-2 bg-cosmos-success/10 border-cosmos-success/30 rounded-lg">
            <span className="text-cosmos-success font-medium">
              已定稿 v{version} ✓
            </span>
          </div>
        )}
      </div>

      {/* Pending Questions UI (P4) */}
      {openQuestions.length > 0 && (
        <div className="glass-panel p-6 bg-space-800/50 border-white/10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-stardust-300 text-lg font-medium">
              待问 {openQuestions.length}
            </h3>
          </div>
          <ul className="space-y-3">
            {openQuestions.map((question, index) => (
              <li key={index} className="flex items-start gap-3">
                <span className="text-nebula-400 mt-1">•</span>
                <span className="text-gray-300 flex-1">{question}</span>
                <button
                  onClick={handleGoAnswer}
                  className="text-stardust-400 hover:text-stardust-300 text-sm font-medium transition-colors"
                >
                  去回答 →
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Graph Display */}
      <div className="h-[70vh]">
        <A1KnowledgeGraph graph={graph} isLoading={false} error={null} />
      </div>

      {/* Graph Legend */}
      <div className="glass-panel p-4">
        <h3 className="text-stardust-300 text-sm font-medium mb-2">图例说明</h3>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-void-400 text-xs">
          <div><span className="text-stardust-300">节点层级：</span>约束 / 世界背景 / 模块 / 设定条目</div>
          <div><span className="text-stardust-300">边类型：</span>实线 = 层级包含 / 虚线 = 约束拓扑</div>
        </div>
      </div>

      {/* Rejected List (Mechanism 4) */}
      {Object.keys(rejectedEdges).length > 0 && (
        <div className="glass-panel p-6 bg-space-800/50 border-white/10">
          <button
            onClick={() => setShowRejectedList(!showRejectedList)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-stardust-300 text-lg font-medium">
              已拒绝清单 ({Object.keys(rejectedEdges).length} 条已拒绝边)
            </h3>
            <span className="text-void-400">{showRejectedList ? '▼' : '▶'}</span>
          </button>

          {showRejectedList && (
            <ul className="mt-4 space-y-3">
              {Object.entries(rejectedEdges).map(([edgeKey, edge]) => (
                <li key={edgeKey} className="flex items-center gap-3 p-3 bg-space-900/50 rounded-lg">
                  <div className="flex-1">
                    <div className="text-gray-300 text-sm">
                      {edge.from_node_id} → {edge.to_node_id}
                    </div>
                    <div className="text-void-400 text-xs">{edge.relation}</div>
                  </div>
                  <button
                    onClick={() => handleRestoreEdge(edgeKey)}
                    className="bg-stardust-400 text-space-950 px-3 py-1 rounded text-sm font-medium hover:bg-stardust-300 transition-colors"
                  >
                    恢复
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
