/**
 * A1 Guided Review API client
 *
 * Provides methods for:
 * - Confirming/rejecting fill proposals in guided chat
 * - Confirming/rejecting concept edges in workspace
 *
 * Backend endpoints: backend/app/api/a1_routes.py
 */

import { fetchWithTimeout, fetchJson } from "./client";
import type { ConceptTerm } from "../types/a1";

const A1_BASE = "/api/a1";
const JSON_HEADERS = { "Content-Type": "application/json" };

/**
 * A dead edge (失效区条目): a previously confirmed edge whose endpoint nodes
 * no longer appear in the graph after a re-finalize.
 * Shape from backend: { key?, from, to, relation, confidence?, reason: "endpoint_missing" }
 */
export interface DeadEdge {
  key?: string;
  from: string;
  to: string;
  relation: string;
  confidence?: string;
  reason: "endpoint_missing";
}

/**
 * Build the canonical edge key for a dead edge (`from/to/relation`),
 * matching the backend `confirmed_edges` key format.
 */
export function getDeadEdgeKey(edge: DeadEdge): string {
  return edge.key ?? `${edge.from}/${edge.to}/${edge.relation}`;
}

/**
 * Discard (废弃) a dead edge: removes it from the backend confirmed_edges
 * snapshot via the existing reject endpoint, so future re-finalizes no
 * longer revive it into the dead zone.
 * POST /api/a1/file/{fileId}/edge/{edgeKey}/reject
 */
export async function discardDeadEdge(
  fileId: string,
  edge: DeadEdge
): Promise<{ rejected: boolean; key: string }> {
  const key = getDeadEdgeKey(edge);
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/edge/${encodeURIComponent(key)}/reject`,
    {
      method: "POST",
      headers: JSON_HEADERS,
    }
  );
  return (await res.json()) as { rejected: boolean; key: string };
}

/**
 * Confirm a fill proposal in guided chat.
 * POST /api/a1/chat/confirm
 *
 * @param sessionId - Active chat session identifier
 * @param proposalKey - Proposal key to confirm (e.g., "world.physics_gravity")
 * @param choice - User choice: "replace" | "merge" | "drop"
 * @returns Confirmation response
 */
export async function confirmFillProposal(
  sessionId: string,
  proposalKey: string,
  choice: "replace" | "merge" | "drop"
): Promise<{ success: boolean; message?: string }> {
  const res = await fetchWithTimeout(`${A1_BASE}/chat/confirm`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      session_id: sessionId,
      kind: "fill",
      proposal: { key: proposalKey },
      choice,
    }),
  });

  return (await res.json()) as { success: boolean; message?: string };
}

/**
 * Confirm a concept edge in workspace.
 * POST /api/a1/file/{fileId}/edge/{edgeKey}/confirm
 *
 * @param fileId - Workspace file identifier
 * @param edgeKey - Edge key (may contain "/" and ".", will be URI-encoded)
 * @returns Confirmation response
 */
export async function confirmEdge(
  fileId: string,
  edgeKey: string
): Promise<{ success: boolean; message?: string }> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/edge/${encodeURIComponent(edgeKey)}/confirm`,
    {
      method: "POST",
      headers: JSON_HEADERS,
    }
  );

  return (await res.json()) as { success: boolean; message?: string };
}

/**
 * Reject a concept edge in workspace.
 * POST /api/a1/file/{fileId}/edge/{edgeKey}/reject
 *
 * @param fileId - Workspace file identifier
 * @param edgeKey - Edge key (may contain "/" and ".", will be URI-encoded)
 * @returns Rejection response
 */
export async function rejectEdge(
  fileId: string,
  edgeKey: string
): Promise<{ success: boolean; message?: string }> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/edge/${encodeURIComponent(edgeKey)}/reject`,
    {
      method: "POST",
      headers: JSON_HEADERS,
    }
  );

  return (await res.json()) as { success: boolean; message?: string };
}

/**
 * Confirm concept terms (Task T-D two-phase flow).
 * POST /api/a1/file/{fileId}/terms/confirm
 *
 * @param fileId - Workspace file identifier
 * @param terms - Specific terms to confirm, or "all" to confirm every term
 * @returns Updated concept_terms list
 */
export async function confirmConceptTerms(
  fileId: string,
  terms: string[] | "all"
): Promise<{ concept_terms: ConceptTerm[] }> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/terms/confirm`,
    {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(terms === "all" ? { all: true } : { terms }),
    }
  );

  return (await res.json()) as { concept_terms: ConceptTerm[] };
}

/**
 * Trigger LLM concept-edge extraction (Task T-D two-phase flow).
 * POST /api/a1/file/{fileId}/concept/extract-edges
 *
 * Backend requires >= 2 confirmed terms (otherwise 400).
 * LLM latency is 30-90s, hence the 180s timeout.
 *
 * @returns { success, edges_count?, warning? }
 */
export async function extractConceptRelations(
  fileId: string
): Promise<{ success: boolean; edges_count?: number; warning?: string }> {
  return fetchJson<{ success: boolean; edges_count?: number; warning?: string }>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/concept/extract-edges`,
    {
      method: "POST",
      headers: JSON_HEADERS,
      timeoutMs: 180_000,
    }
  );
}
