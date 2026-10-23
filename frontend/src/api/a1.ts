/**
 * A1 Guided Review API client
 *
 * Provides methods for:
 * - Confirming/rejecting fill proposals in guided chat
 * - Confirming/rejecting concept edges in workspace
 *
 * Backend endpoints: backend/app/api/a1_routes.py
 */

import { fetchWithTimeout, fetchJson, fetchText } from "./client";
import type {
  ConceptTerm,
  ClosingState,
  ResolveAlignmentResponse,
  ImpulseSignalResponse,
  DraftVersion,
  ImpulseCoords,
  NudgeSignal,
  MergeUndoResponse,
  DocArtifactResponse,
  TemplateArtifactResponse,
} from "../types/a1";

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
  // fetchJson (not fetchWithTimeout) so failures throw ApiError with a
  // status — the review panel's error copy depends on distinguishing 404
  // (stale backend / vanished edge) from network errors.
  return fetchJson<{ success: boolean; message?: string }>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/edge/${encodeURIComponent(edgeKey)}/confirm`,
    {
      method: "POST",
      headers: JSON_HEADERS,
    }
  );
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
  return fetchJson<{ success: boolean; message?: string }>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/edge/${encodeURIComponent(edgeKey)}/reject`,
    {
      method: "POST",
      headers: JSON_HEADERS,
    }
  );
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

// ---------------------------------------------------------------------------
// D21 endpoints (plan task T7)
// ---------------------------------------------------------------------------

/**
 * Closing-question state snapshot (zero LLM, pure projection).
 * GET /api/a1/file/{fileId}/closing-state
 *
 * Uses fetchWithTimeout: a 404 (unknown file) surfaces as the degraded
 * Error("HTTP 404") — call sites only need pass/fail here.
 */
export async function getClosingState(fileId: string): Promise<ClosingState> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/closing-state`,
    { method: "GET" }
  );
  return (await res.json()) as ClosingState;
}

/**
 * Resolve (accept/discard) a pending alignment proposal.
 * POST /api/a1/file/{fileId}/alignment/{key}/resolve  body {accept}
 *
 * Uses fetchJson so HTTP failures throw ApiError with .status — resolve
 * panels distinguish 404 (stale file) from network errors. A stale/unknown
 * key is NOT an HTTP error: backend returns 200 + {applied:false, error:"not_found"}.
 */
export async function resolveAlignment(
  fileId: string,
  key: string,
  accept: boolean
): Promise<ResolveAlignmentResponse> {
  return fetchJson<ResolveAlignmentResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/alignment/${encodeURIComponent(key)}/resolve`,
    {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ accept }),
    }
  );
}

/**
 * User nudge signal for the impulse coords (three-value discrete buttons).
 * POST /api/a1/file/{fileId}/impulse-coords/signal  body {signal}
 *
 * Illegal signal → 400 ApiError (compile-time union prevents it; runtime
 * guard kept server-side). Guardrail damping (per-session cap / cooldown)
 * is a 200 + applied=false — honest passthrough, no error.
 */
export async function nudgeCoords(
  fileId: string,
  signal: NudgeSignal
): Promise<ImpulseSignalResponse> {
  return fetchJson<ImpulseSignalResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/impulse-coords/signal`,
    {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({ signal }),
    }
  );
}

/**
 * In-session draft version label ("α0.1" / "α0.11" style).
 * GET /api/a1/file/{fileId}/draft-version
 *
 * Outside draft phase → {available:false}; unknown file → degraded 404 Error.
 */
export async function getDraftVersion(fileId: string): Promise<DraftVersion> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/draft-version`,
    { method: "GET" }
  );
  return (await res.json()) as DraftVersion;
}

/**
 * Impulse coords dashboard (three-piece + audit trail, read-only).
 * GET /api/a1/file/{fileId}/impulse-coords
 *
 * First frontend reference to this pre-existing endpoint. Legacy sessions
 * are lazily initialized server-side (deterministic lookup, no LLM).
 */
export async function getImpulseCoords(fileId: string): Promise<ImpulseCoords> {
  const res = await fetchWithTimeout(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/impulse-coords`,
    { method: "GET" }
  );
  return (await res.json()) as ImpulseCoords;
}

/**
 * D23: undo a semantic auto-merge disclosed in the chat flow.
 * POST /api/a1/merge/undo  body {session_id, token}
 *
 * Idempotent: an unknown/already-undone token is still HTTP 200 with
 * {restored:false}; HTTP failures surface as ApiError via fetchJson.
 */
export async function mergeUndo(
  sessionId: string,
  token: string
): Promise<MergeUndoResponse> {
  return fetchJson<MergeUndoResponse>(`${A1_BASE}/merge/undo`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ session_id: sessionId, token }),
  });
}

// ---------------------------------------------------------------------------
// Doc / artifact generation endpoints (IP poster 「生成文档」 panel)
// ---------------------------------------------------------------------------

/**
 * Generate the main module document (主模组 M).
 * POST /api/a1/file/{fileId}/doc  (no body)
 *
 * Contract: {doc_code, graph_id, used_stale, ledger}.
 * Not finalized → 409 ApiError with body {detail: "pending_finalize"}.
 * LLM latency possible (seconds) — caller must show a loading state.
 */
export async function generateDoc(fileId: string): Promise<DocArtifactResponse> {
  return fetchJson<DocArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/doc`,
    { method: "POST", headers: JSON_HEADERS, timeoutMs: 180_000 }
  );
}

/**
 * Fetch the generated main module document as markdown text.
 * GET /api/a1/file/{fileId}/doc  → text/markdown plain text.
 * Not generated yet → 409 ApiError {detail: "pending_finalize"}.
 */
export async function fetchDocMarkdown(fileId: string): Promise<string> {
  return fetchText(`${A1_BASE}/file/${encodeURIComponent(fileId)}/doc`);
}

/**
 * Generate the world bible (世界圣经 B).
 * POST /api/a1/file/{fileId}/world-bible → {bible_code, graph_id, ...}.
 */
export async function generateWorldBible(fileId: string): Promise<DocArtifactResponse> {
  return fetchJson<DocArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/world-bible`,
    { method: "POST", headers: JSON_HEADERS, timeoutMs: 180_000 }
  );
}

/** GET /api/a1/file/{fileId}/world-bible → markdown text. */
export async function fetchWorldBibleMarkdown(fileId: string): Promise<string> {
  return fetchText(`${A1_BASE}/file/${encodeURIComponent(fileId)}/world-bible`);
}

/**
 * Generate the character codex (人物志 C).
 * POST /api/a1/file/{fileId}/character-codex → {codex_code, graph_id, ...}.
 */
export async function generateCharacterCodex(fileId: string): Promise<DocArtifactResponse> {
  return fetchJson<DocArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/character-codex`,
    { method: "POST", headers: JSON_HEADERS, timeoutMs: 180_000 }
  );
}

/** GET /api/a1/file/{fileId}/character-codex → markdown text. */
export async function fetchCharacterCodexMarkdown(fileId: string): Promise<string> {
  return fetchText(`${A1_BASE}/file/${encodeURIComponent(fileId)}/character-codex`);
}

/**
 * Generate the story outline (故事大纲 O).
 * POST /api/a1/file/{fileId}/story-outline → {outline_code, graph_id, ...}.
 */
export async function generateStoryOutline(fileId: string): Promise<DocArtifactResponse> {
  return fetchJson<DocArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/story-outline`,
    { method: "POST", headers: JSON_HEADERS, timeoutMs: 180_000 }
  );
}

/** GET /api/a1/file/{fileId}/story-outline → markdown text. */
export async function fetchStoryOutlineMarkdown(fileId: string): Promise<string> {
  return fetchText(`${A1_BASE}/file/${encodeURIComponent(fileId)}/story-outline`);
}

/**
 * Generate the dice template (骰子模板 TD) — deterministic projection,
 * zero LLM (instant). POST /api/a1/file/{fileId}/dice-template.
 *
 * Contract: {graph_code, template, used_stale, warnings}. No GET — the POST
 * response payload IS the artifact; render `template` directly.
 */
export async function generateDiceTemplate(fileId: string): Promise<TemplateArtifactResponse> {
  return fetchJson<TemplateArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/dice-template`,
    { method: "POST", headers: JSON_HEADERS }
  );
}

/**
 * Generate the character template (角色模板 TC).
 * POST /api/a1/file/{fileId}/character-template.
 *
 * Hard dependency on dice template: backend returns 409
 * {detail: "missing_dice_template"} when no dice artifact exists — caller
 * may auto-generate the dice template once and retry once.
 */
export async function generateCharacterTemplate(
  fileId: string
): Promise<TemplateArtifactResponse> {
  return fetchJson<TemplateArtifactResponse>(
    `${A1_BASE}/file/${encodeURIComponent(fileId)}/character-template`,
    { method: "POST", headers: JSON_HEADERS, timeoutMs: 180_000 }
  );
}
