/**
 * GraphAssetReview page for graph-driven asset generation.
 *
 * Features:
 * - Graph selection and loading
 * - Wave-based asset display with WaveDivider components
 * - NodeBadge status indicators
 * - PromptPreview for prompt visualization
 * - Serial generation triggering and progress tracking
 * - Regeneration support for failed nodes
 *
 * Routing: /admin/graph-assets
 */

import { useCallback, useMemo, useState } from "react";
import { AssetPlaceholder } from "../components/AssetPlaceholder";
import { NodeBadge } from "../components/graph/NodeBadge";
import { WaveDivider } from "../components/graph/WaveDivider";
import { PromptPreview } from "../components/graph/PromptPreview";
import {
  loadGraph,
  generateGraph,
} from "../api/graph";
import type {
  KnowledgeGraph,
  GraphNode,
  NodeStatus,
  GraphEdge,
} from "../types/graph";

// Mock list of available graphs (in real app, this would come from an API endpoint)
const AVAILABLE_GRAPHS = [
  { scene_id: "scene_001", name: "赛博朋克神庙废墟" },
  { scene_id: "scene_002", name: "量子实验室核心区" },
  { scene_id: "scene_003", name: "数据流废墟入口" },
];

// Mock asset results for completed nodes (in real app, these would come from generation results)
interface GeneratedAsset {
  nodeId: string;
  status: NodeStatus;
  imageUrl?: string;
  promptPreview?: {
    subject: string;
    relations: string[];
    background: string;
  };
  errorMessage?: string;
}

/**
 * Group nodes by generation wave based on dependencies.
 * Wave 0: Background node (if exists)
 * Wave 1+: Nodes grouped by dependency levels (simplified topological grouping)
 */
function groupNodesByWaves(graph: KnowledgeGraph): GraphNode[][] {
  const waves: GraphNode[][] = [];
  const processed = new Set<string>();

  // Wave 0: Background node (always first if exists)
  if (graph.background_node_id && graph.nodes[graph.background_node_id]) {
    waves.push([graph.nodes[graph.background_node_id]]);
    processed.add(graph.background_node_id);
  }

  // Group remaining nodes by dependencies (simplified approach)
  const remaining = Object.values(graph.nodes).filter(
    (node) => !processed.has(node.id)
  ) as GraphNode[];

  // Simple greedy grouping: nodes with no unprocessed dependencies go in current wave
  let currentWave: GraphNode[] = [];
  let waveIndex = 1;

  while (remaining.length > 0) {
    currentWave = [];
    const toRemove: string[] = [];

    for (const node of remaining) {
      // Check if all dependencies are processed
      const dependencies = getDependencies(node.id, graph);
      const dependenciesProcessed = dependencies.every((depId) =>
        processed.has(depId)
      );

      if (dependenciesProcessed) {
        currentWave.push(node);
        toRemove.push(node.id);
        processed.add(node.id);
      }
    }

    if (currentWave.length > 0) {
      waves.push(currentWave);
      // Remove processed nodes from remaining
      remaining.splice(
        0,
        remaining.length,
        ...remaining.filter((node) => !toRemove.includes(node.id))
      );
    } else {
      // Circular dependency or orphan nodes - add remaining as next wave
      waves.push([...remaining]);
      remaining.forEach((node) => processed.add(node.id));
      remaining.splice(0, remaining.length);
    }

    waveIndex++;
  }

  return waves;
}

/**
 * Get dependencies (incoming edges) for a node.
 */
function getDependencies(nodeId: string, graph: KnowledgeGraph): string[] {
  return graph.edges
    .filter((edge: GraphEdge) => edge.to_node_id === nodeId)
    .map((edge: GraphEdge) => edge.from_node_id);
}

/**
 * Generate mock prompt preview for a node (in real app, this would come from the backend).
 */
function generateMockPromptPreview(
  node: GraphNode,
  graph: KnowledgeGraph
): GeneratedAsset["promptPreview"] {
  // Mock implementation - in real app, this would come from PromptFusion service
  return {
    subject: node.description,
    relations: graph.edges
      .filter((edge: GraphEdge) => edge.to_node_id === node.id)
      .map((edge: GraphEdge) => {
        const fromNode = graph.nodes[edge.from_node_id];
        return edge.visual_description || `Visual relation from ${fromNode?.serial_number || edge.from_node_id}`;
      }),
    background: graph.background_node_id
      ? graph.nodes[graph.background_node_id]?.description || ""
      : "",
  };
}

export function GraphAssetReview() {
  // Graph selection state
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [loadingGraph, setLoadingGraph] = useState<boolean>(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  // Generation state
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationResults, setGenerationResults] = useState<
    Record<string, GeneratedAsset>
  >({});
  const [notice, setNotice] = useState<string | null>(null);

  // Available graphs (in real app, would fetch from API)
  const availableGraphs = AVAILABLE_GRAPHS;

  // Compute waves for the current graph
  const waves = useMemo(() => {
    return graph ? groupNodesByWaves(graph) : [];
  }, [graph]);

  // ── Graph loading ─────────────────────────────────────────────────────
  const handleLoadGraph = useCallback(async (sceneId: string) => {
    setLoadingGraph(true);
    setGraphError(null);
    try {
      const loadedGraph = await loadGraph(sceneId);
      setGraph(loadedGraph);
      setSelectedSceneId(sceneId);
      setGenerationResults({}); // Clear previous results
      setNotice(`✓ Loaded graph: ${sceneId}`);
      setTimeout(() => setNotice(null), 3000);
    } catch (err) {
      setGraphError(err instanceof Error ? err.message : "Failed to load graph");
      setGraph(null);
    } finally {
      setLoadingGraph(false);
    }
  }, []);

  // ── Generation triggering ────────────────────────────────────────────────
  const handleGenerateGraph = useCallback(async () => {
    if (!graph) return;

    setGenerating(true);
    setGenerationResults({});
    try {
      const result = await generateGraph(graph);

      // Mock generation results based on response
      const mockResults: Record<string, GeneratedAsset> = {};

      // Initialize all nodes with generating status
      Object.values(graph.nodes).forEach((node) => {
        mockResults[node.id] = {
          nodeId: node.id,
          status: "generating",
          promptPreview: generateMockPromptPreview(node, graph),
        };
      });

      // Simulate generation completion (in real app, would poll for updates)
      setTimeout(() => {
        const updatedResults = { ...mockResults };

        // Mark nodes as completed or failed based on API response
        result.order.forEach((nodeId, index) => {
          if (updatedResults[nodeId]) {
            const isSuccess = index < result.succeeded;
            updatedResults[nodeId] = {
              ...updatedResults[nodeId],
              status: isSuccess ? "completed" : "failed",
              imageUrl: isSuccess
                ? `/assets/mock_${nodeId}.png`
                : undefined,
              errorMessage: isSuccess
                ? undefined
                : "Generation failed - try again",
            };
          }
        });

        setGenerationResults(updatedResults);
        setNotice(
          `✓ Generation complete: ${result.succeeded}/${result.total} succeeded`
        );
        setTimeout(() => setNotice(null), 5000);
      }, 3000); // Mock 3-second generation time

      setNotice(`▶ Generation started: ${result.total} nodes`);
      setTimeout(() => setNotice(null), 3000);
    } catch (err) {
      setGraphError(
        err instanceof Error ? err.message : "Generation failed"
      );
    } finally {
      // Keep generating true until mock completes
      setTimeout(() => setGenerating(false), 3500);
    }
  }, [graph]);

  // ── Individual node regeneration ────────────────────────────────────────
  const handleRegenerateNode = useCallback(
    async (nodeId: string) => {
      if (!graph || generating) return;

      const node = graph.nodes[nodeId];
      if (!node) return;

      // Update status to generating
      setGenerationResults((prev) => ({
        ...prev,
        [nodeId]: {
          ...prev[nodeId],
          status: "generating",
        },
      }));

      // Mock regeneration
      setTimeout(() => {
        const success = Math.random() > 0.3; // 70% success rate
        setGenerationResults((prev) => ({
          ...prev,
          [nodeId]: {
            ...prev[nodeId],
            status: success ? "completed" : "failed",
            imageUrl: success
              ? `/assets/mock_${nodeId}_regenerated.png`
              : prev[nodeId].imageUrl,
            errorMessage: success
              ? undefined
              : "Regeneration failed - try again",
          },
        }));

        setNotice(
          success
            ? `✓ Regenerated node: ${node.serial_number}`
            : `✗ Regeneration failed: ${node.serial_number}`
        );
        setTimeout(() => setNotice(null), 3000);
      }, 2000);
    },
    [graph, generating]
  );

  // ── Render helpers ────────────────────────────────────────────────────────
  const renderNodeCard = (
    node: GraphNode,
    result: GeneratedAsset | undefined
  ) => {
    return (
      <div
        key={node.id}
        className="bg-black border-2 border-neon-green/30 rounded-sm p-4 hover:border-neon-cyan transition-colors"
      >
        {/* Node header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-neon-cyan font-mono text-lg">
              {node.serial_number}
            </span>
            <NodeBadge status={result?.status || node.status} />
          </div>
          {result?.status === "failed" && (
            <button
              type="button"
              onClick={() => void handleRegenerateNode(node.id)}
              disabled={generating}
              className="text-xs border border-neon-red text-neon-red px-2 py-1 hover:bg-neon-red hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Regenerate
            </button>
          )}
        </div>

        {/* Node description */}
        <div className="text-gray-400 font-mono text-sm mb-3 line-clamp-2">
          {node.description}
        </div>

        {/* Prompt preview (if available) */}
        {result?.promptPreview && (
          <div className="mb-3">
            <PromptPreview
              subject={result.promptPreview.subject}
              relations={result.promptPreview.relations}
              background={result.promptPreview.background}
              className="text-xs"
              collapseThreshold={150}
            />
          </div>
        )}

        {/* Generated image or placeholder */}
        <div className="relative aspect-video bg-black/50 border border-neon-green/20 rounded-sm overflow-hidden">
          {result?.imageUrl ? (
            <img
              src={result.imageUrl}
              alt={`${node.serial_number} - generated`}
              className="w-full h-full object-cover"
            />
          ) : result?.status === "generating" ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-neon-cyan font-mono text-sm animate-pulse">
                Generating...
              </div>
            </div>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <AssetPlaceholder
                mode={node.level === 1 ? "background" : "object"}
                name={node.serial_number}
                type={node.level === 1 ? "background" : "object"}
                className="static max-w-xs max-h-xs opacity-50"
              />
            </div>
          )}

          {/* Error overlay */}
          {result?.status === "failed" && result.errorMessage && (
            <div className="absolute bottom-0 left-0 right-0 bg-neon-red/90 backdrop-blur-sm p-2">
              <div className="text-white font-mono text-xs">
                ⚠ {result.errorMessage}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen w-screen bg-black text-neon-green font-mono overflow-hidden flex flex-col">
      {/* Top Bar */}
      <header className="flex justify-between items-center px-6 py-3 border-b-2 border-neon-green shrink-0">
        <div className="flex items-baseline gap-4">
          <h1 className="text-2xl text-neon-cyan text-glow-cyan tracking-widest">
            资产生成页面变体 // 回声
          </h1>
          {generating && (
            <span className="text-xs text-neon-cyan animate-pulse tracking-widest">
              ⟳ 生成中…
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {notice && (
            <span className="text-xs text-neon-green/80 tracking-widest">
              {notice}
            </span>
          )}
          <a
            href="/"
            className="text-neon-green text-sm border border-neon-green px-3 py-1 hover:bg-neon-green hover:text-black transition-colors"
          >
            ← 返回游戏
          </a>
          <button
            type="button"
            onClick={() => void handleGenerateGraph()}
            disabled={!graph || generating}
            className={`text-sm border px-3 py-1 transition-colors ${
              graph && !generating
                ? "border-neon-cyan text-neon-cyan hover:bg-neon-cyan hover:text-black"
                : "border-neon-cyan/40 text-neon-cyan/40 cursor-not-allowed"
            }`}
          >
            {generating ? "生成中…" : "生成所有"}
          </button>
        </div>
      </header>

      {/* Error display */}
      {graphError && (
        <div className="px-6 py-2 bg-neon-red/10 border-b border-neon-red text-neon-red text-xs tracking-widest flex justify-between items-center">
          <span>⚠ {graphError}</span>
          <button
            type="button"
            onClick={() => setGraphError(null)}
            className="text-neon-red/70 hover:text-neon-red underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Graph Selection */}
        <aside className="w-80 border-r-2 border-neon-green flex flex-col overflow-hidden">
          <div className="p-3 border-b border-neon-green">
            <div className="text-xs text-neon-green mb-2 opacity-70">
              GRAPH SELECTION
            </div>
            <div className="space-y-2">
              {availableGraphs.map((graphInfo) => (
                <button
                  key={graphInfo.scene_id}
                  type="button"
                  onClick={() => void handleLoadGraph(graphInfo.scene_id)}
                  disabled={loadingGraph}
                  className={`w-full text-left p-3 border-2 bg-black transition-colors ${
                    selectedSceneId === graphInfo.scene_id
                      ? "border-neon-cyan bg-neon-cyan/5"
                      : "border-neon-green/30 hover:border-neon-cyan"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="text-sm text-neon-green truncate">
                    {graphInfo.name}
                  </div>
                  <div className="text-xs text-gray-500 uppercase">
                    {graphInfo.scene_id}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Graph info panel */}
          {graph && (
            <div className="p-3 border-b border-neon-green">
              <div className="text-xs text-neon-green mb-2 opacity-70">
                GRAPH INFO
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Scene ID:</span>
                  <span className="text-neon-cyan">{graph.scene_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Nodes:</span>
                  <span className="text-neon-cyan">
                    {Object.keys(graph.nodes).length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Edges:</span>
                  <span className="text-neon-cyan">{graph.edges.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Waves:</span>
                  <span className="text-neon-cyan">{waves.length}</span>
                </div>
              </div>
            </div>
          )}

          {/* Loading indicator */}
          {loadingGraph && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-neon-cyan text-xs animate-pulse">
                加载图谱中…
              </div>
            </div>
          )}

          {/* Empty state */}
          {!graph && !loadingGraph && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-neon-green/50 text-xs text-center">
                选择一个图谱开始
                <br />
                <span className="opacity-60">— 等待选择 —</span>
              </div>
            </div>
          )}
        </aside>

        {/* Right Content - Wave Display */}
        <main className="flex-1 overflow-y-auto p-6">
          {!graph ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-neon-green/50 text-center">
                <div className="text-6xl mb-4 opacity-30">◇</div>
                <div className="text-xl tracking-widest">选择图谱</div>
                <div className="text-sm opacity-60 mt-2">
                  从左侧面板选择一个已保存的图谱
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Generation waves */}
              {waves.map((waveNodes, waveIndex) => (
                <div key={`wave-${waveIndex}`}>
                  <WaveDivider
                    waveNumber={waveIndex}
                    label={
                      waveIndex === 0 && graph.background_node_id
                        ? "Wave 0: Background"
                        : `Wave ${waveIndex}`
                    }
                  />

                  {/* Wave content grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                    {waveNodes.map((node) =>
                      renderNodeCard(node, generationResults[node.id])
                    )}
                  </div>
                </div>
              ))}

              {/* Empty state if no waves */}
              {waves.length === 0 && (
                <div className="text-center text-neon-green/50 text-sm">
                  此图谱没有节点
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}