/**
 * Graph-driven asset pipeline type definitions.
 *
 * Backend model correspondence:
 * - GraphNode → backend.app.models.knowledge_graph.GraphNode
 * - GraphEdge → backend.app.models.knowledge_graph.GraphEdge
 * - KnowledgeGraph → backend.app.models.knowledge_graph.KnowledgeGraph
 * - NodeStatus → backend.app.models.knowledge_graph.NodeStatus (enum)
 * - EdgeType → backend.app.models.knowledge_graph.EdgeType (enum)
 */

/**
 * Node lifecycle status.
 * Backend: NodeStatus enum (PENDING, GENERATING, COMPLETED, FAILED)
 */
export type NodeStatus = "pending" | "generating" | "completed" | "failed";

/**
 * Edge type between nodes.
 * Backend: EdgeType enum (TREE, CROSS)
 */
export type EdgeType = "tree" | "cross";

/**
 * Single node in the knowledge graph.
 * Backend: GraphNode Pydantic model
 */
export interface GraphNode {
  /** Unique node identifier derived from serial_number */
  id: string;
  /** Hierarchical serial like "1-1-1" */
  serial_number: string;
  /** Depth level (1-indexed by segment count) */
  level: number;
  /** Visual description of the asset */
  description: string;
  /** Current lifecycle status */
  status: NodeStatus;
}

/**
 * Directed edge between two nodes.
 * Backend: GraphEdge Pydantic model
 */
export interface GraphEdge {
  /** Source node ID */
  from_node_id: string;
  /** Target node ID */
  to_node_id: string;
  /** Tree (hierarchy) or cross (visual dependency) */
  edge_type: EdgeType;
  /** User-written visual relationship description */
  visual_description: string;
  /** Optional: Natural language relationship label ("belongs_to", "contains", "inspires") */
  relation?: string;
  /** Optional: Edge confidence source ("rule" | "semantic" | "semantic" | "") */
  confidence?: 'rule' | 'semantic' | 'structure' | '';
  /** Optional: User confirmation flag for AI-suggested edges */
  confirmed?: boolean;
}

/**
 * Knowledge graph for a scene with nodes, edges, and metadata.
 * Backend: KnowledgeGraph Pydantic model
 */
export interface KnowledgeGraph {
  /** Scene this graph belongs to */
  scene_id: string;
  /** Dict of node_id -> GraphNode */
  nodes: Record<string, GraphNode>;
  /** List of graph edges */
  edges: GraphEdge[];
  /** ID of the background root node (level 1) */
  background_node_id?: string;
}

/**
 * API request/response types for graph endpoints.
 * Backend: graph_routes.py request/response models
 */

/** POST /api/graph/extract request */
export interface ExtractGraphRequest {
  scene_description: string;
}

/** POST /api/graph/validate response */
export interface ValidateGraphResponse {
  is_valid: boolean;
  cycles: unknown[][]; // Array of node ID arrays representing cycles
}

/** POST /api/graph/save response */
export interface SaveGraphResponse {
  scene_id: string;
  saved: boolean;
}

/** DELETE /api/graph/{scene_id} response */
export interface DeleteGraphResponse {
  deleted: boolean;
}

/** POST /api/graph/generate response */
export interface GenerateGraphResponse {
  total: number;
  succeeded: number;
  failed: number;
  order: string[]; // Node IDs in generation order
  error?: string;
}
