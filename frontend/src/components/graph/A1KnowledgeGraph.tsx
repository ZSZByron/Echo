/**
 * A1 Knowledge Graph Component
 *
 * Read-only knowledge graph visualization using React Flow.
 * Displays A1 worldview nodes with hierarchical topology and constraint relationships.
 */

import React, { useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import type { KnowledgeGraph, GraphNode, GraphEdge } from '../../types/graph';
import 'reactflow/dist/style.css';

export interface A1KnowledgeGraphProps {
  graph: KnowledgeGraph | null;
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
}

/**
 * Parse constraint description into display format
 * Format: "[A1] Constraint(LAW.world_structure=value)" -> "LAW.world_structure: value"
 */
const parseConstraintDescription = (description: string): { dimension: string; key: string; value: string } => {
  const match = description.match(/Constraint\((\w+)\.(\w+)=([^)]+)\)/);
  if (match) {
    return { dimension: match[1], key: match[2], value: match[3] };
  }
  // Fallback for malformed constraint strings
  const parts = description.split('=');
  if (parts.length === 2) {
    const leftParts = parts[0].split('.');
    return {
      dimension: leftParts[leftParts.length - 2] || 'UNKNOWN',
      key: leftParts[leftParts.length - 1] || 'UNKNOWN',
      value: parts[1].replace(')', '')
    };
  }
  return { dimension: 'UNKNOWN', key: 'UNKNOWN', value: description };
};

/**
 * Calculate node position based on level-based layout algorithm
 */
const calculateNodePosition = (
  level: number,
  indexInLevel: number,
  totalInLevel: number,
  parentX?: number
): { x: number; y: number } => {
  const LEVEL_Y_POSITIONS: Record<number, number> = {
    0: -260,  // Constraints at top
    1: 0,     // Background root
    2: 240,   // Modules
    3: 500    // Entries
  };

  const MODULE_SPACING = 280;
  const ENTRY_SPACING = 170;

  const y = LEVEL_Y_POSITIONS[level] ?? 0;

  let x = 0;

  if (level === 1) {
    // Background root: center
    x = 0;
  } else if (level === 2) {
    // Modules: evenly spaced, centered
    const totalWidth = (totalInLevel - 1) * MODULE_SPACING;
    x = (indexInLevel * MODULE_SPACING) - (totalWidth / 2);
  } else if (level === 3 && parentX !== undefined) {
    // Entries: under their parent module
    const totalWidth = (totalInLevel - 1) * ENTRY_SPACING;
    x = parentX + (indexInLevel * ENTRY_SPACING) - (totalWidth / 2);
  } else if (level === 0) {
    // Constraints: evenly spaced at top
    const totalWidth = (totalInLevel - 1) * MODULE_SPACING;
    x = (indexInLevel * MODULE_SPACING) - (totalWidth / 2);
  }

  return { x, y };
};

export function A1KnowledgeGraph({ graph, isLoading, error, onRetry }: A1KnowledgeGraphProps) {
  /**
   * Transform GraphNode to ReactFlow Node with styling based on level
   */
  const toReactFlowNode = useCallback((node: GraphNode): Node => {
    const isConstraint = node.id.startsWith('cst_') || node.level === 0;

    let nodeStyle: React.CSSProperties = {};
    let label = '';

    if (node.level === 1) {
      // Background root node: golden border
      nodeStyle = {
        border: '2px solid var(--color-stardust-400)',
        backgroundColor: 'rgba(19, 19, 42, 0.95)',
        borderRadius: '8px',
        padding: '12px',
        minWidth: '200px',
        boxShadow: '0 0 10px rgba(251, 191, 36, 0.3)'
      };
      label = `✦ ${node.description}`;
    } else if (node.level === 2) {
      // Module node: purple border
      nodeStyle = {
        border: '2px solid rgba(167, 139, 250, 0.6)',
        backgroundColor: 'rgba(28, 28, 61, 0.8)',
        borderRadius: '6px',
        padding: '10px',
        minWidth: '160px',
        boxShadow: '0 0 8px rgba(139, 92, 246, 0.2)'
      };
      label = `▤ ${node.description}`;
    } else if (node.level === 3) {
      // Entry node: thin white border, parse description
      const parts = node.description.split(':');
      if (parts.length >= 2) {
        const entryLabel = parts[0].trim();
        const entryValue = parts.slice(1).join(':').trim();
        nodeStyle = {
          border: '1px solid rgba(255, 255, 255, 0.15)',
          backgroundColor: 'rgba(19, 19, 42, 0.7)',
          borderRadius: '4px',
          padding: '8px',
          minWidth: '140px',
          maxWidth: '180px',
          fontSize: '13px'
        };
        label = `· ${entryLabel}: ${entryValue}`;
      } else {
        nodeStyle = {
          border: '1px solid rgba(255, 255, 255, 0.15)',
          backgroundColor: 'rgba(19, 19, 42, 0.7)',
          borderRadius: '4px',
          padding: '8px',
          minWidth: '140px'
        };
        label = `· ${node.description}`;
      }
    } else if (isConstraint) {
      // Constraint node: amber border
      const parsed = parseConstraintDescription(node.description);
      nodeStyle = {
        border: '2px solid rgba(245, 158, 11, 0.6)',
        backgroundColor: 'rgba(28, 28, 61, 0.8)',
        borderRadius: '6px',
        padding: '8px',
        minWidth: '160px',
        fontSize: '12px',
        boxShadow: '0 0 8px rgba(245, 158, 11, 0.2)'
      };
      label = `⚙ [${parsed.dimension}] ${parsed.key}: ${parsed.value}`;
    }

    return {
      id: node.id,
      type: 'default',
      position: { x: 0, y: 0 }, // Will be set by layout
      data: {
        label: (
          <div style={{
            color: 'white',
            fontFamily: 'ui-sans-serif, system-ui, sans-serif',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {label}
          </div>
        )
      },
      style: nodeStyle
    };
  }, []);

  /**
   * Transform GraphEdge to ReactFlow Edge
   */
  const toReactFlowEdge = useCallback((edge: GraphEdge): Edge => {
    const isTree = edge.edge_type === 'tree';

    return {
      id: `${edge.from_node_id}-${edge.to_node_id}`,
      source: edge.from_node_id,
      target: edge.to_node_id,
      type: 'smoothstep',
      animated: !isTree,
      style: {
        stroke: isTree ? '#a78bfa' : '#f59e0b',
        strokeWidth: isTree ? 2 : 1.5,
        strokeDasharray: isTree ? undefined : '6,4'
      },
      label: isTree ? undefined : edge.visual_description,
      labelStyle: {
        fontSize: '10px',
        fontFamily: 'ui-monospace, Consolas, monospace',
        fill: '#888'
      }
    };
  }, []);

  /**
   * Calculate layout positions for all nodes
   */
  const layoutNodes = useCallback((
    nodes: GraphNode[],
    edges: GraphEdge[]
  ): Node[] => {
    // Group nodes by level
    const nodesByLevel = nodes.reduce((acc, node) => {
      if (!acc[node.level]) {
        acc[node.level] = [];
      }
      acc[node.level].push(node);
      return acc;
    }, {} as Record<number, GraphNode[]>);

    // Build parent mapping for level 3 nodes
    const parentMap = new Map<string, string>();
    edges.forEach(edge => {
      if (edge.edge_type === 'tree') {
        const targetNode = nodes.find(n => n.id === edge.to_node_id);
        if (targetNode && targetNode.level === 3) {
          parentMap.set(edge.to_node_id, edge.from_node_id);
        }
      }
    });

    // Calculate positions
    const positionedNodes: Node[] = [];

    // Level 1: Background root
    if (nodesByLevel[1]) {
      nodesByLevel[1].forEach((node, index) => {
        const pos = calculateNodePosition(node.level, index, nodesByLevel[1].length);
        const rfNode = toReactFlowNode(node);
        rfNode.position = pos;
        positionedNodes.push(rfNode);
      });
    }

    // Level 2: Modules
    const modulePositions = new Map<string, number>();
    if (nodesByLevel[2]) {
      nodesByLevel[2].forEach((node, index) => {
        const pos = calculateNodePosition(node.level, index, nodesByLevel[2].length);
        const rfNode = toReactFlowNode(node);
        rfNode.position = pos;
        positionedNodes.push(rfNode);
        modulePositions.set(node.id, pos.x);
      });
    }

    // Level 3: Entries (grouped by parent module)
    if (nodesByLevel[3]) {
      const entriesByModule = nodesByLevel[3].reduce((acc, node) => {
        const parentId = parentMap.get(node.id);
        if (!parentId) return acc;

        if (!acc[parentId]) {
          acc[parentId] = [];
        }
        acc[parentId].push(node);
        return acc;
      }, {} as Record<string, GraphNode[]>);

      Object.entries(entriesByModule).forEach(([parentId, children]) => {
        const parentX = modulePositions.get(parentId);
        children.forEach((node, index) => {
          const pos = calculateNodePosition(node.level, index, children.length, parentX);
          const rfNode = toReactFlowNode(node);
          rfNode.position = pos;
          positionedNodes.push(rfNode);
        });
      });
    }

    // Level 0: Constraints
    if (nodesByLevel[0]) {
      nodesByLevel[0].forEach((node, index) => {
        const pos = calculateNodePosition(node.level, index, nodesByLevel[0].length);
        const rfNode = toReactFlowNode(node);
        rfNode.position = pos;
        positionedNodes.push(rfNode);
      });
    }

    return positionedNodes;
  }, [toReactFlowNode]);

  /**
   * Memoize flow nodes and edges from graph data
   */
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!graph) {
      return { flowNodes: [], flowEdges: [] };
    }

    const graphNodes = Object.values(graph.nodes);
    const flowEdges = graph.edges.map(toReactFlowEdge);
    const flowNodes = layoutNodes(graphNodes, graph.edges);

    return { flowNodes, flowEdges };
  }, [graph, toReactFlowEdge, layoutNodes]);

  /**
   * Loading state
   */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-stardust-400 text-sm">构建知识图谱中...</p>
        </div>
      </div>
    );
  }

  /**
   * Error state
   */
  if (error) {
    return (
      <div className="glass-panel p-6 m-4 flex flex-col items-center gap-4">
        <p className="text-cosmos-error text-center">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-nebula-500 hover:bg-nebula-400 text-white rounded-md transition-colors"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  /**
   * Empty state
   */
  if (!graph) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <p className="text-void-400 text-sm">暂无图谱数据</p>
      </div>
    );
  }

  /**
   * Render React Flow graph
   */
  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        edgesFocusable={false}
        panOnScroll
        zoomOnScroll
        minZoom={0.2}
        maxZoom={1.5}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="rgba(255,255,255,0.1)" />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const nodeData = graph.nodes[node.id];
            if (!nodeData) return '#a78bfa';

            if (nodeData.level === 1) return 'var(--color-stardust-400)';
            if (nodeData.level === 2) return 'var(--color-nebula-400)';
            if (nodeData.level === 3 || nodeData.id.startsWith('cst_')) return '#ffffff';
            return '#a78bfa';
          }}
          maskColor="rgba(19, 19, 42, 0.8)"
        />
      </ReactFlow>
    </div>
  );
}
