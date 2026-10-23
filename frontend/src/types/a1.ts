/**
 * D21 frontend-phase types (plan task T7).
 *
 * Field-for-field alignment with backend responses:
 * - ClosingState / ClosingPreview → a1_routes.get_closing_state (L1163) +
 *   closing_gate.build_output_preview (L209-240)
 * - AlignmentItem → a1_routes._pending_alignments_payload (L1129-1147)
 * - ResolveAlignmentResponse → a1_routes.alignment_resolve (L1186-1205)
 * - ImpulseSignalResponse → a1_routes.post_impulse_signal (L1221-1244)
 * - DraftVersion → a1_routes.get_draft_version (L1247-1267) +
 *   draft_version.draft_label (baseline/round are ints)
 * - ImpulseCoords → a1_routes.get_impulse_coords (L1058-1070) +
 *   impulse_coords.dashboard_data (L322-331)
 *
 * NOTE: chat-response closing signal uses `step`/`settled` keys
 * (_closing_signal, L1150-1160) — distinct from ClosingState's
 * `closing_step`/`closing_settled`. Kept as separate shapes on purpose.
 */

/** D21⑩ user nudge signal — closed whitelist (a1_routes L1216-1218). */
export type NudgeSignal =
  | "user_nudge_story"
  | "user_nudge_builder"
  | "user_nudge_confirm";

/** Downstream consumer artifact registered against a finalized graph. */
export interface ConsumerArtifact {
  id: string;
  kind: string;
}

/** Dual-condition closing gate breakdown (closing_gate.closing_status L65-72). */
export interface ClosingStatus {
  questions_complete: boolean;
  pending_count: number;
  complete: boolean;
}

/** Per-module coverage row (closing_gate._coverage L150-158). */
export interface ModuleCoverage {
  module_id: string;
  done_ratio: number;
  done_fields: number;
  total_fields: number;
}

/** A subfield gap in the recipe (closing_gate._gap_list L173-178). */
export interface OutputGap {
  module_id: string;
  field: string;
  key: string;
  label: string;
}

/** Version chain projection (closing_gate L239-246); null when no graph yet. */
export interface VersionChain {
  graph_code: string | null;
  ip_code: string | null;
  instance_no: number | null;
  version: number | null;
  superseded_by: string | null;
  status: string;
}

/** Output preview — the closing question's single data source (9 keys). */
export interface ClosingPreview {
  file_id: string;
  exists: boolean;
  closing: ClosingStatus;
  module_coverage: ModuleCoverage[];
  gaps: OutputGap[];
  version_chain: VersionChain | null;
  stale: boolean;
  stale_warning: string | null;
  consumers: ConsumerArtifact[];
}

/** GET /api/a1/file/{id}/closing-state response. */
export interface ClosingState {
  file_id: string;
  closing_step: number;
  closing_settled: boolean;
  triggered: boolean;
  preview: ClosingPreview;
}

/** A pending alignment proposal in the chat response (`pending_alignments`). */
export interface AlignmentItem {
  key: string;
  action: "link" | "dedupe" | "contradict" | "update";
  content: string;
  quote: string;
  stale_warning: string[];
}

/** POST /api/a1/file/{id}/alignment/{key}/resolve response. */
export interface ResolveAlignmentResponse {
  applied: boolean;
  accept: boolean;
  /** "not_found" when the key is stale/unknown (still HTTP 200). */
  error?: string;
}

/** POST /api/a1/file/{id}/impulse-coords/signal response. */
export interface ImpulseSignalResponse {
  file_id: string;
  session_id: string;
  applied: boolean;
  axis: number;
  confidence: number;
}

/**
 * GET /api/a1/file/{id}/draft-version response.
 * `version` comes from draft_label(): "α0.{round}" or "α0.{round}{n}".
 */
export type DraftVersion =
  | { available: false }
  | { available: true; version: string; baseline: number; round: number };

/** One audit-trail entry (impulse_coords audit append sites L168-239). */
export interface ImpulseAuditEntry {
  round: number;
  signal: string;
  key: string;
  axis_before: number;
  confidence_before: number;
  applied: boolean;
  axis_after: number;
  confidence_after: number;
  /** Present only on applied entries. */
  axis_delta?: number;
  /** Present only on safety-raise entries. */
  reason?: string;
}

/** GET /api/a1/file/{id}/impulse-coords dashboard response. */
export interface ImpulseCoords {
  file_id: string;
  session_id: string;
  axis: number;
  confidence: number;
  safety_flag: boolean;
  anchor: number;
  anchor_source: string;
  adjustments: number;
  reorder_count: number;
  audit: ImpulseAuditEntry[];
}

/**
 * A1 Guided Review — Concept Network types
 *
 * Backend model correspondence:
 * - A1Proposal → backend.app.domains.a1.proposal.Proposal
 * - OpenQuestion → backend.app.domains.a1.chat.OpenQuestion
 * - EdgeStats → backend.app.domains.a1.concept.EdgeStats
 * - GraphEdge (extended) → backend.app.models.knowledge_graph.GraphEdge
 */

/**
 * Proposal for filling missing concept slots.
 * Used in guided chat flow for user confirmation.
 */
export interface A1Proposal {
  /** Unique proposal key (e.g., "world.physics_gravity") */
  key: string;
  /** Target module (world/story/scene/npc/asset/constraint) */
  module: string;
  /** Subfield within module (e.g., "physics", "culture", "motivation") */
  subfield: string;
  /** Current/old value (empty or existing placeholder) */
  old: string;
  /** Proposed new value (AI-generated suggestion) */
  new: string;
  /** Optional conflict explanation if this collides with existing concepts */
  conflict_note: string | null;
  /** Human-readable preview of merged result */
  merge_preview: string;
  /** Available choices for this proposal (e.g., ["replace", "merge", "drop"]) */
  options?: string[];
  /**
   * D23: LLM-drafted human-language question shown instead of the generic
   * copy when non-empty; the three action buttons stay unchanged.
   */
  question_text?: string;
}

/**
 * Open question tracked during guided review.
 * Questions that require clarification from the user.
 */
export interface OpenQuestion {
  /** Unique question identifier */
  id: string;
  /** Question text */
  question: string;
  /** Current tracking status */
  status: 'pending' | 'answered' | 'skipped';
  /** ISO timestamp when question was created */
  created_at: string;
  /** Optional answer text (when status is 'answered') */
  answer?: string;
}

/**
 * Statistics for concept edges in a workspace.
 * Tracks edge types and confirmation status.
 */
export interface EdgeStats {
  /** Total semantic edges (AI-inferred relationships) */
  semantic_total: number;
  /** Semantic edges confirmed by user */
  semantic_confirmed: number;
  /** Total rule-based edges (hardcoded constraints) */
  rule_total: number;
  /** Total structure edges (hierarchical dependencies) */
  structure_total: number;
  /** Edges awaiting user review */
  pending_review: number;
}

/**
 * Concept term extracted from finalized worldview (Task T-B/T-D two-phase flow).
 * Returned by GET /api/a1/file/{id} as `concept_terms`.
 */
export interface ConceptTerm {
  /** The concept word itself (e.g., "死亡转生") */
  term: string;
  /** Source structured field key the term was extracted from */
  field_key: string;
  /** Short gloss/explanation of the term */
  gloss: string;
  /** Whether the user has confirmed this term into the dictionary */
  confirmed: boolean;
}

/**
 * A concept relation proposed by LLM edge extraction (pre-confirmation).
 * Returned by GET /api/a1/file/{id} as `proposed_relations`.
 */
export interface ProposedRelation {
  /** Relation name (e.g., "触发") — may be a new relation word not yet in dictionary */
  name: string;
  /** Source concept term */
  from_term: string;
  /** Target concept term */
  to_term: string;
  /** Rationale for why this relation was proposed */
  rationale: string;
}

/** POST /api/a1/merge/undo response (idempotent 200). */
export interface MergeUndoResponse {
  restored: boolean;
  /** Field whose value was restored (present on success). */
  field_key?: string;
}

/**
 * One recursive answer entry in the file-state `answers_tree` projection
 * (GET /api/a1/file/{id}): a human answer plus its nested child entries.
 */
export interface AnswerNode {
  text: string;
  children: AnswerNode[];
  /** Origin marker (e.g. chat / upload); optional additive field. */
  source?: string;
}

/**
 * D23: semantic auto-merge disclosure from the chat response (`auto_merges`).
 * Backend merges a user utterance into an existing field and discloses it
 * inline; the user can undo via POST /api/a1/merge/undo {session_id, token}.
 */
export interface AutoMergeDisclosure {
  token: string;
  field_key: string;
  label: string;
  old: string;
  new: string;
  merged: string;
  kind: string;
}

/**
 * Structured warning ledger entry — merged view of degradation disclosures
 * from five channels (assemble / finalize / graphify / dead_edges / upload).
 * Returned by GET /api/a1/file/{id} as `warnings`.
 */
export interface WarningLedgerEntry {
  /** Origin channel of the warning */
  source: string;
  /** Human-readable detail (Chinese, full text) */
  detail: string;
  /** Number of occurrences (display ×N when > 1) */
  count: number;
  /** Severity: "warn" (prominent) or "info" (weakened) */
  level: string;
}

/**
 * Doc/artifact generation response (POST /api/a1/file/{id}/doc|world-bible|
 * character-codex|story-outline). The code field name varies per endpoint
 * (doc_code / bible_code / codex_code / outline_code).
 */
export interface DocArtifactResponse {
  doc_code?: string;
  bible_code?: string;
  codex_code?: string;
  outline_code?: string;
  graph_id: string;
  used_stale: boolean;
  ledger: WarningLedgerEntry[];
}

/**
 * Structured template response (POST /api/a1/file/{id}/dice-template |
 * character-template). No GET counterpart — the POST payload IS the artifact.
 */
export interface TemplateArtifactResponse {
  graph_code: string;
  template: Record<string, unknown>;
  used_stale: boolean;
  warnings: WarningLedgerEntry[];
}
