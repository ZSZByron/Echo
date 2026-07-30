/**
 * Graph API client for graph-driven asset pipeline.
 *
 * Provides methods for:
 * - Extracting graphs from text descriptions via LLM
 * - Validating graphs for cycle detection
 * - Saving/loading graphs from database
 * - Deleting graphs
 * - Triggering serial generation
 *
 * Backend endpoints: backend/app/api/graph_routes.py
 */

import { fetchWithTimeout } from "./client";
import type {
  KnowledgeGraph,
  ExtractGraphRequest,
  ValidateGraphResponse,
  SaveGraphResponse,
  DeleteGraphResponse,
  GenerateGraphResponse,
} from "../types/graph";

const GRAPH_BASE = "/api/graph";
const JSON_HEADERS = { "Content-Type": "application/json" };

/**
 * Extract a knowledge graph skeleton from free-text scene description via LLM.
 * POST /api/graph/extract
 *
 * @param sceneDescription - Free-text description of the scene
 * @returns KnowledgeGraph with nodes and edges
 */
export async function extractGraph(
  sceneDescription: string
): Promise<KnowledgeGraph> {
  const body: ExtractGraphRequest = { scene_description: sceneDescription };

  const res = await fetchWithTimeout(`${GRAPH_BASE}/extract`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

  return (await res.json()) as KnowledgeGraph;
}

/**
 * Validate a knowledge graph for cycle detection.
 * POST /api/graph/validate
 *
 * @param graph - KnowledgeGraph to validate
 * @returns Validation result with cycle information
 */
export async function validateGraph(
  graph: KnowledgeGraph
): Promise<ValidateGraphResponse> {
  const res = await fetchWithTimeout(`${GRAPH_BASE}/validate`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(graph),
  });

  return (await res.json()) as ValidateGraphResponse;
}

/**
 * Save a knowledge graph to the database.
 * Performs cycle validation before saving.
 * POST /api/graph/save
 *
 * @param graph - KnowledgeGraph to save
 * @returns Save confirmation with scene_id
 */
export async function saveGraph(
  graph: KnowledgeGraph
): Promise<SaveGraphResponse> {
  const res = await fetchWithTimeout(`${GRAPH_BASE}/save`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(graph),
  });

  return (await res.json()) as SaveGraphResponse;
}

/**
 * Load a knowledge graph from the database by scene_id.
 * GET /api/graph/{scene_id}
 *
 * @param sceneId - Scene identifier
 * @returns KnowledgeGraph with nodes and edges
 */
export async function loadGraph(sceneId: string): Promise<KnowledgeGraph> {
  const res = await fetchWithTimeout(
    `${GRAPH_BASE}/${encodeURIComponent(sceneId)}`,
    { method: "GET" }
  );

  return (await res.json()) as KnowledgeGraph;
}

/**
 * Delete a knowledge graph from the database by scene_id.
 * DELETE /api/graph/{scene_id}
 *
 * @param sceneId - Scene identifier
 * @returns Delete confirmation
 */
export async function deleteGraph(
  sceneId: string
): Promise<DeleteGraphResponse> {
  const res = await fetchWithTimeout(
    `${GRAPH_BASE}/${encodeURIComponent(sceneId)}`,
    {
      method: "DELETE",
    }
  );

  return (await res.json()) as DeleteGraphResponse;
}

/**
 * Trigger serial wave-based generation for a knowledge graph.
 * POST /api/graph/generate
 *
 * @param graph - KnowledgeGraph to generate
 * @returns Generation results with counts and execution order
 */
export async function generateGraph(
  graph: KnowledgeGraph
): Promise<GenerateGraphResponse> {
  const res = await fetchWithTimeout(`${GRAPH_BASE}/generate`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(graph),
  });

  return (await res.json()) as GenerateGraphResponse;
}
