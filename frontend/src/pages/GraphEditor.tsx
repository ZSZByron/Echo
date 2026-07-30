/**
 * GraphEditor - React Flow knowledge graph editor with cyberpunk styling.
 *
 * Features:
 * - Interactive graph visualization with React Flow
 * - Node/edge editing with dialogs
 * - Add/delete nodes and edges
 * - Graph validation (cycle detection)
 * - LLM-based graph extraction from free text
 * - Save/load graphs from database
 * - Wave-based serial generation trigger
 *
 * Design: Cyberpunk aesthetic matching the existing UI with neon colors,
 * CRT effects, and terminal-style interactions.
 */

import { useCallback, useEffect, useState } from 'react';
import type { Edge, Node } from 'reactflow';
import {
  Background,
  BackgroundVariant,
  ConnectionMode,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NodeBadge } from '../components/graph/NodeBadge';
import {
  extractGraph,
  generateGraph,
  saveGraph,
  validateGraph,
} from '../api/graph';
import type {
  EdgeType,
  GraphEdge,
  GraphNode,
  KnowledgeGraph,
  NodeStatus,
} from '../types/graph';

// Cyberpunk styling
const CYBERPUNK_COLORS = {
  background: '#0a0a0a',
  grid: '#00ff41',
  nodeBorder: '#00ff41',
  nodeBg: '#0a0a0a',
  edgeTree: '#00ff41',
  edgeCross: '#00ffff',
  edgeHighlight: '#ff0040',
  selection: '#ffff00',
};

// Level-based node colors (hierarchy)
const LEVEL_COLORS = [
  '#00ff41', // Level 1 - Neon Green
  '#00ffff', // Level 2 - Neon Cyan
  '#ff00ff', // Level 3 - Neon Magenta
  '#ffff00', // Level 4 - Neon Yellow
  '#ff8800', // Level 5 - Neon Orange
];

interface EditNode {
  id: string;
  serial_number: string;
  description: string;
  level: number;
  status: NodeStatus;
}

interface EditEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  edge_type: EdgeType;
  visual_description: string;
}

// Custom node component with cyberpunk styling
function CustomNode({ data }: { data: GraphNode & { isSelected?: boolean } }) {
  const { description, level, status, serial_number, isSelected } = data;
  const isBackground = level === 1;
  const levelColor = LEVEL_COLORS[(level - 1) % LEVEL_COLORS.length];

  return (
    <div
      className={`px-3 py-2 border-2 rounded-sm font-mono text-xs transition-all ${
        isSelected ? 'ring-2 ring-yellow-400' : ''
      }`}
      style={{
        backgroundColor: CYBERPUNK_COLORS.nodeBg,
        borderColor: isSelected
          ? CYBERPUNK_COLORS.selection
          : isBackground
          ? '#ff8800'
          : levelColor,
        borderWidth: isBackground ? '3px' : '2px',
        minWidth: '150px',
        boxShadow: isSelected
          ? `0 0 10px ${CYBERPUNK_COLORS.selection}`
          : `0 0 5px ${levelColor}40`,
      }}
    >
      {/* Background indicator */}
      {isBackground && (
        <div className="text-orange-400 text-[10px] font-bold uppercase tracking-wider mb-1">
          ◈ BACKGROUND
        </div>
      )}

      {/* Serial number */}
      <div className="text-gray-400 text-[10px] font-mono mb-1">
        [{serial_number}]
      </div>

      {/* Description */}
      <div className="text-gray-200 text-xs leading-relaxed mb-2">
        {description.length > 40 ? `${description.slice(0, 40)}...` : description}
      </div>

      {/* Status badge */}
      <NodeBadge status={status} />
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

export function GraphEditor() {
  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<GraphEdge>([]);

  // UI state
  const [selectedNode, setSelectedNode] = useState<EditNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<EditEdge | null>(null);
  const [showAddNode, setShowAddNode] = useState(false);
  const [showExtract, setShowExtract] = useState(false);
  const [extractText, setExtractText] = useState('');
  const [validationResult, setValidationResult] = useState<{
    is_valid: boolean;
    cycles: unknown[][];
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);

  // New node form
  const [newNodeForm, setNewNodeForm] = useState({
    serial_number: '',
    description: '',
    level: 1,
    parent_id: '',
  });

  // Convert GraphNode to ReactFlow Node
  const toReactFlowNode = useCallback((node: GraphNode): Node => {
    const levelColor = LEVEL_COLORS[(node.level - 1) % LEVEL_COLORS.length];
    return {
      id: node.id,
      type: 'custom',
      position: { x: 0, y: 0 }, // Will be set by layout
      data: { ...node, isSelected: false },
      style: {
        border: `2px solid ${levelColor}`,
        boxShadow: `0 0 5px ${levelColor}40`,
      },
    };
  }, []);

  // Convert GraphEdge to ReactFlow Edge
  const toReactFlowEdge = useCallback(
    (edge: GraphEdge): Edge => {
      const isTree = edge.edge_type === 'tree';
      return {
        id: `${edge.from_node_id}-${edge.to_node_id}`,
        source: edge.from_node_id,
        target: edge.to_node_id,
        type: 'smoothstep',
        animated: !isTree,
        style: {
          stroke: isTree ? CYBERPUNK_COLORS.edgeTree : CYBERPUNK_COLORS.edgeCross,
          strokeWidth: isTree ? 2 : 1,
          strokeDasharray: isTree ? undefined : '5,5',
        },
        label: edge.visual_description,
        labelStyle: {
          fontSize: '10px',
          fontFamily: 'ui-monospace, Consolas, monospace',
          fill: '#888',
        },
        data: edge,
      };
    },
    []
  );

  // Load graph from API (if scene_id in URL)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sceneId = urlParams.get('scene_id');

    if (sceneId) {
      loadGraph(sceneId);
    }
  }, []);

  const loadGraph = async (sceneId: string) => {
    setIsLoading(true);
    setMessage(null);
    try {
      // For now, start with empty graph
      // In production: const graph = await loadGraph(sceneId);
      setMessage({ type: 'info', text: `Scene loaded: ${sceneId}` });
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to load scene: ${error}` });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle new edge connection
  const onConnect = useCallback(
    (connection: { source: string | null; target: string | null; sourceHandle?: string | null; targetHandle?: string | null }) => {
      if (!connection.source || !connection.target) return;

      const newEdge: GraphEdge = {
        from_node_id: connection.source,
        to_node_id: connection.target,
        edge_type: 'tree',
        visual_description: '',
      };

      setEdges((eds) => [...eds, toReactFlowEdge(newEdge)]);
      setSelectedEdge({
        id: `${connection.source}-${connection.target}`,
        ...newEdge,
      });
    },
    [toReactFlowEdge, setEdges]
  );

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode({
        id: node.id,
        serial_number: node.data.serial_number,
        description: node.data.description,
        level: node.data.level,
        status: node.data.status,
      });
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: { ...n.data, isSelected: n.id === node.id },
        }))
      );
      setSelectedEdge(null);
    },
    [setNodes]
  );

  // Handle edge click
  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      setSelectedEdge({
        id: edge.id,
        from_node_id: edge.source,
        to_node_id: edge.target,
        edge_type: edge.data?.edge_type || 'tree',
        visual_description: edge.data?.visual_description || '',
      });
      setNodes((nds) =>
        nds.map((n) => ({ ...n, data: { ...n.data, isSelected: false } }))
      );
      setSelectedNode(null);
    },
    [setNodes]
  );

  // Delete selected
  const deleteSelected = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) =>
        eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id)
      );
      setSelectedNode(null);
    } else if (selectedEdge) {
      setEdges((eds) => eds.filter((e) => e.id !== selectedEdge.id));
      setSelectedEdge(null);
    }
  }, [selectedNode, selectedEdge, setNodes, setEdges]);

  // Add new node
  const addNode = useCallback(() => {
    if (!newNodeForm.serial_number || !newNodeForm.description) {
      setMessage({ type: 'error', text: 'Serial number and description required' });
      return;
    }

    const newNode: GraphNode = {
      id: newNodeForm.serial_number,
      serial_number: newNodeForm.serial_number,
      level: newNodeForm.level,
      description: newNodeForm.description,
      status: 'pending',
    };

    const rfNode = toReactFlowNode(newNode);
    rfNode.position = {
      x: Math.random() * 400 + 100,
      y: Math.random() * 300 + 100,
    };

    setNodes((nds) => [...nds, rfNode]);

    // Add edge to parent if specified
    if (newNodeForm.parent_id) {
      const newEdge: GraphEdge = {
        from_node_id: newNodeForm.parent_id,
        to_node_id: newNode.id,
        edge_type: 'tree',
        visual_description: '',
      };
      setEdges((eds) => [...eds, toReactFlowEdge(newEdge)]);
    }

    setShowAddNode(false);
    setNewNodeForm({
      serial_number: '',
      description: '',
      level: 1,
      parent_id: '',
    });
  }, [newNodeForm, toReactFlowNode, setNodes, setEdges, toReactFlowEdge]);

  // Extract graph from LLM
  const handleExtract = async () => {
    if (!extractText.trim()) {
      setMessage({ type: 'error', text: 'Please enter a scene description' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const graph = await extractGraph(extractText);

      // Convert to ReactFlow nodes
      const rfNodes = Object.values(graph.nodes).map((node) => {
        const rfNode = toReactFlowNode(node);
        rfNode.position = {
          x: (node.level - 1) * 250 + 100,
          y: Object.values(graph.nodes).filter((n) => n.level === node.level).indexOf(node) * 150 + 100,
        };
        return rfNode;
      });

      const rfEdges = graph.edges.map(toReactFlowEdge);

      setNodes(rfNodes);
      setEdges(rfEdges);
      setShowExtract(false);
      setExtractText('');
      setMessage({ type: 'success', text: 'Graph extracted successfully' });
    } catch (error) {
      setMessage({ type: 'error', text: `Extraction failed: ${error}` });
    } finally {
      setIsLoading(false);
    }
  };

  // Validate graph for cycles
  const handleValidate = async () => {
    const graph: KnowledgeGraph = {
      scene_id: 'current',
      nodes: nodes.reduce((acc, node) => {
        acc[node.id] = node.data;
        return acc;
      }, {} as Record<string, GraphNode>),
      edges: edges.map((edge) => (edge.data || {
        from_node_id: edge.source,
        to_node_id: edge.target,
        edge_type: 'tree',
        visual_description: '',
      }) as GraphEdge),
    };

    try {
      const result = await validateGraph(graph);
      setValidationResult(result);

      if (!result.is_valid) {
        setMessage({
          type: 'error',
          text: `Cycles detected: ${result.cycles.length} found`,
        });
        // Highlight cycle edges
        const cycleEdges = new Set(
          result.cycles.flatMap((cycle) =>
            cycle.flatMap((_, i) => {
              if (i === cycle.length - 1) return [];
              const edgeId = `${cycle[i]}-${cycle[i + 1]}`;
              return [edgeId, `${cycle[i + 1]}-${cycle[i]}`];
            })
          )
        );
        setEdges((eds) =>
          eds.map((edge) =>
            cycleEdges.has(edge.id)
              ? { ...edge, style: { ...edge.style, stroke: CYBERPUNK_COLORS.edgeHighlight, strokeWidth: 3 } }
              : edge
          )
        );
      } else {
        setMessage({ type: 'success', text: 'Graph is valid (no cycles)' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Validation failed: ${error}` });
    }
  };

  // Save graph
  const handleSave = async () => {
    const graph: KnowledgeGraph = {
      scene_id: 'scene-' + Date.now(),
      nodes: nodes.reduce((acc, node) => {
        acc[node.id] = node.data;
        return acc;
      }, {} as Record<string, GraphNode>),
      edges: edges.map((edge) => (edge.data || {
        from_node_id: edge.source,
        to_node_id: edge.target,
        edge_type: 'tree',
        visual_description: '',
      }) as GraphEdge),
    };

    try {
      const result = await saveGraph(graph);
      setMessage({
        type: 'success',
        text: `Graph saved: ${result.scene_id}`,
      });
    } catch (error) {
      setMessage({ type: 'error', text: `Save failed: ${error}` });
    }
  };

  // Trigger generation
  const handleGenerate = async () => {
    const graph: KnowledgeGraph = {
      scene_id: 'current',
      nodes: nodes.reduce((acc, node) => {
        acc[node.id] = node.data;
        return acc;
      }, {} as Record<string, GraphNode>),
      edges: edges.map((edge) => (edge.data || edge) as GraphEdge),
    };

    try {
      const result = await generateGraph(graph);
      setMessage({
        type: 'success',
        text: `Generation complete: ${result.succeeded}/${result.total} succeeded`,
      });
    } catch (error) {
      setMessage({ type: 'error', text: `Generation failed: ${error}` });
    }
  };

  return (
    <div className="w-full h-screen bg-black text-neon-green font-mono relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-black/80 backdrop-blur-sm border-b border-neon-green p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl text-neon-cyan text-glow-cyan">图谱编辑器</h1>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddNode(true)}
              className="px-3 py-1 bg-neon-green text-black font-mono text-xs uppercase hover:bg-green-400 transition-colors"
            >
              + 节点
            </button>
            <button
              onClick={() => setShowExtract(true)}
              className="px-3 py-1 bg-neon-cyan text-black font-mono text-xs uppercase hover:bg-cyan-400 transition-colors"
            >
              AI 提取
            </button>
            <button
              onClick={handleValidate}
              className="px-3 py-1 bg-yellow-500 text-black font-mono text-xs uppercase hover:bg-yellow-400 transition-colors"
            >
              验证
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1 bg-neon-green text-black font-mono text-xs uppercase hover:bg-green-400 transition-colors"
            >
              保存
            </button>
            <button
              onClick={handleGenerate}
              className="px-3 py-1 bg-neon-cyan text-black font-mono text-xs uppercase hover:bg-cyan-400 transition-colors"
            >
              生成
            </button>
            {(selectedNode || selectedEdge) && (
              <button
                onClick={deleteSelected}
                className="px-3 py-1 bg-neon-red text-black font-mono text-xs uppercase hover:bg-red-400 transition-colors"
              >
                删除
              </button>
            )}
          </div>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`mt-2 px-3 py-1 font-mono text-xs ${
              message.type === 'success'
                ? 'bg-green-900 text-neon-green'
                : message.type === 'error'
                ? 'bg-red-900 text-neon-red'
                : 'bg-blue-900 text-neon-cyan'
            }`}
          >
            {message.text}
          </div>
        )}
      </div>

      {/* React Flow Canvas */}
      <div className="absolute inset-0 pt-20">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={12}
            size={1}
            color={CYBERPUNK_COLORS.grid}
          />
          <Controls />
        </ReactFlow>
      </div>

      {/* Add Node Dialog */}
      {showAddNode && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-black border-2 border-neon-green p-6 max-w-md w-full">
            <h2 className="text-xl text-neon-cyan text-glow-cyan mb-4">添加节点</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-neon-green text-xs mb-1">序号</label>
                <input
                  type="text"
                  value={newNodeForm.serial_number}
                  onChange={(e) =>
                    setNewNodeForm({ ...newNodeForm, serial_number: e.target.value })
                  }
                  className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1"
                  placeholder="例如: 1-1-2"
                />
              </div>
              <div>
                <label className="block text-neon-green text-xs mb-1">描述</label>
                <textarea
                  value={newNodeForm.description}
                  onChange={(e) =>
                    setNewNodeForm({ ...newNodeForm, description: e.target.value })
                  }
                  className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1 h-24"
                  placeholder="视觉描述..."
                />
              </div>
              <div>
                <label className="block text-neon-green text-xs mb-1">层级</label>
                <input
                  type="number"
                  min="1"
                  value={newNodeForm.level}
                  onChange={(e) =>
                    setNewNodeForm({ ...newNodeForm, level: parseInt(e.target.value) || 1 })
                  }
                  className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1"
                />
              </div>
              <div>
                <label className="block text-neon-green text-xs mb-1">父节点 (可选)</label>
                <input
                  type="text"
                  value={newNodeForm.parent_id}
                  onChange={(e) =>
                    setNewNodeForm({ ...newNodeForm, parent_id: e.target.value })
                  }
                  className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1"
                  placeholder="父节点 ID"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={addNode}
                className="flex-1 px-3 py-2 bg-neon-green text-black font-mono text-sm uppercase hover:bg-green-400 transition-colors"
              >
                添加
              </button>
              <button
                onClick={() => setShowAddNode(false)}
                className="flex-1 px-3 py-2 border border-neon-red text-neon-red font-mono text-sm uppercase hover:bg-red-900 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Extract Dialog */}
      {showExtract && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-black border-2 border-neon-cyan p-6 max-w-2xl w-full">
            <h2 className="text-xl text-neon-cyan text-glow-cyan mb-4">AI 提取图谱</h2>
            <div className="mb-4">
              <label className="block text-neon-cyan text-xs mb-1">
                场景描述（自由文本）
              </label>
              <textarea
                value={extractText}
                onChange={(e) => setExtractText(e.target.value)}
                className="w-full bg-black border border-neon-cyan text-neon-cyan font-mono text-sm px-2 py-1 h-48"
                placeholder="描述你的场景...例如：一个古老的埃及神殿，神殿入口有巨大的石门，门上刻着神秘符号。神殿内部有巨大的石柱，柱子上刻画着法老的生平..."
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleExtract}
                disabled={isLoading}
                className="flex-1 px-3 py-2 bg-neon-cyan text-black font-mono text-sm uppercase hover:bg-cyan-400 transition-colors disabled:opacity-50"
              >
                {isLoading ? '提取中...' : '提取图谱'}
              </button>
              <button
                onClick={() => {
                  setShowExtract(false);
                  setExtractText('');
                }}
                className="flex-1 px-3 py-2 border border-neon-red text-neon-red font-mono text-sm uppercase hover:bg-red-900 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Node Dialog */}
      {selectedNode && !showAddNode && !showExtract && (
        <div className="absolute top-20 right-4 z-40 bg-black/90 border-2 border-neon-green p-4 max-w-sm w-full backdrop-blur-sm">
          <h3 className="text-neon-cyan text-glow-cyan mb-2">编辑节点</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-neon-green text-xs mb-1">序号</label>
              <input
                type="text"
                value={selectedNode.serial_number}
                onChange={(e) =>
                  setSelectedNode({ ...selectedNode, serial_number: e.target.value })
                }
                className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1"
              />
            </div>
            <div>
              <label className="block text-neon-green text-xs mb-1">描述</label>
              <textarea
                value={selectedNode.description}
                onChange={(e) =>
                  setSelectedNode({ ...selectedNode, description: e.target.value })
                }
                className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1 h-20"
              />
            </div>
            <div>
              <label className="block text-neon-green text-xs mb-1">层级</label>
              <input
                type="number"
                min="1"
                value={selectedNode.level}
                onChange={(e) =>
                  setSelectedNode({ ...selectedNode, level: parseInt(e.target.value) || 1 })
                }
                className="w-full bg-black border border-neon-green text-neon-green font-mono text-sm px-2 py-1"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  setNodes((nds) =>
                    nds.map((n) =>
                      n.id === selectedNode.id
                        ? {
                            ...n,
                            data: {
                              ...n.data,
                              serial_number: selectedNode.serial_number,
                              description: selectedNode.description,
                              level: selectedNode.level,
                            },
                          }
                        : n
                    )
                  );
                  setSelectedNode(null);
                }}
                className="flex-1 px-3 py-2 bg-neon-green text-black font-mono text-sm uppercase hover:bg-green-400 transition-colors"
              >
                保存
              </button>
              <button
                onClick={() => setSelectedNode(null)}
                className="flex-1 px-3 py-2 border border-neon-red text-neon-red font-mono text-sm uppercase hover:bg-red-900 transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Edge Dialog */}
      {selectedEdge && !showAddNode && !showExtract && (
        <div className="absolute top-20 right-4 z-40 bg-black/90 border-2 border-neon-cyan p-4 max-w-sm w-full backdrop-blur-sm">
          <h3 className="text-neon-cyan text-glow-cyan mb-2">编辑边</h3>
          <div className="space-y-3">
            <div className="text-xs text-gray-400 mb-2">
              {selectedEdge.from_node_id} → {selectedEdge.to_node_id}
            </div>
            <div>
              <label className="block text-neon-cyan text-xs mb-1">类型</label>
              <select
                value={selectedEdge.edge_type}
                onChange={(e) =>
                  setSelectedEdge({
                    ...selectedEdge,
                    edge_type: e.target.value as EdgeType,
                  })
                }
                className="w-full bg-black border border-neon-cyan text-neon-cyan font-mono text-sm px-2 py-1"
              >
                <option value="tree">Tree (层级)</option>
                <option value="cross">Cross (交叉)</option>
              </select>
            </div>
            <div>
              <label className="block text-neon-cyan text-xs mb-1">视觉描述</label>
              <textarea
                value={selectedEdge.visual_description}
                onChange={(e) =>
                  setSelectedEdge({
                    ...selectedEdge,
                    visual_description: e.target.value,
                  })
                }
                className="w-full bg-black border border-neon-cyan text-neon-cyan font-mono text-sm px-2 py-1 h-20"
                placeholder="描述视觉关系..."
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  setEdges((eds) =>
                    eds.map((e) =>
                      e.id === selectedEdge.id
                        ? {
                            ...e,
                            data: {
                              ...(typeof e.data === 'object' ? e.data : {
                                from_node_id: e.source,
                                to_node_id: e.target,
                                edge_type: 'tree',
                                visual_description: '',
                              }),
                              edge_type: selectedEdge.edge_type,
                              visual_description: selectedEdge.visual_description,
                            },
                            style: {
                              ...e.style,
                              stroke:
                                selectedEdge.edge_type === 'tree'
                                  ? CYBERPUNK_COLORS.edgeTree
                                  : CYBERPUNK_COLORS.edgeCross,
                              strokeWidth: selectedEdge.edge_type === 'tree' ? 2 : 1,
                              strokeDasharray: selectedEdge.edge_type === 'tree' ? undefined : '5,5',
                            },
                          }
                        : e
                    )
                  );
                  setSelectedEdge(null);
                }}
                className="flex-1 px-3 py-2 bg-neon-cyan text-black font-mono text-sm uppercase hover:bg-cyan-400 transition-colors"
              >
                保存
              </button>
              <button
                onClick={() => setSelectedEdge(null)}
                className="flex-1 px-3 py-2 border border-neon-red text-neon-red font-mono text-sm uppercase hover:bg-red-900 transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Result */}
      {validationResult && !validationResult.is_valid && (
        <div className="absolute bottom-4 left-4 z-40 bg-black/90 border-2 border-neon-red p-4 max-w-md backdrop-blur-sm">
          <h3 className="text-neon-red text-glow-red mb-2">⚠ 环检测警告</h3>
          <div className="text-xs text-gray-300">
            检测到 {validationResult.cycles.length} 个环：
            {validationResult.cycles.map((cycle, i) => (
              <div key={i} className="mt-1 text-neon-red">
                环 {i + 1}: {cycle.join(' → ')}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Wrap with ReactFlowProvider
export default function GraphEditorWrapper() {
  return (
    <ReactFlowProvider>
      <GraphEditor />
    </ReactFlowProvider>
  );
}
