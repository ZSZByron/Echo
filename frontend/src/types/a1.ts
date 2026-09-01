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
