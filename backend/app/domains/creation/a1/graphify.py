"""SIR contract models and helpers for graphify (A1 v0.5).

Contract source (authoritative, verbatim field names):
    docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md §4

Five result fields of one ``graphify_llm`` call:
    module_summaries / entries / edges / constraint_fields / open_questions

Phase 1 notes:
    - ``children`` nesting is parsed but NOT consumed (validation returns a
      warning instead of raising — see :func:`validate_children_depth`).
    - All list fields default to empty (contract D4: missing = empty,
      partial-accept semantics).
    - This module intentionally does NOT import concept_edge_vocab: the
      relation vocabulary is injected as a parameter (T2 edits it in
      parallel; avoid coupling).
"""

from __future__ import annotations

import os
import re

from pydantic import BaseModel, Field

from app.domains.creation.graph.constraint_topology import STRUCTURED_FIELDS
from app.domains.creation.seed.a1_question_tree import all_subfield_keys

# =============================================================================
# Constants
# =============================================================================

#: LLM call timeout in seconds. Overridable via ``GRAPHIFY_TIMEOUT`` env var.
GRAPHIFY_TIMEOUT: int = int(os.environ.get("GRAPHIFY_TIMEOUT", "60"))

#: Placeholder title when sanitization leaves nothing usable.
_UNNAMED_PLACEHOLDER = "未命名"

#: Maximum characters kept in a sanitized title.
_TITLE_MAX_LEN = 32

_WHITESPACE_RE = re.compile(r"\s+")


# =============================================================================
# Output Models (Pydantic v2)
# =============================================================================


class EntryItem(BaseModel):
    """One depth-tree item under an anchor.

    Attributes:
        title: Node title (raw LLM output; sanitize before id minting).
        content: Item body text.
        children: Nested sub-items. Phase 1 parses this field but the
            assembler rejects (warns on) any non-empty children — depth is
            only opened in Phase 2.
    """

    title: str
    content: str = ""
    children: list[EntryItem] = Field(default_factory=list)


class AnchorEntries(BaseModel):
    """All entries grouped under one ``module.subfield`` anchor."""

    anchor: str
    items: list[EntryItem] = Field(default_factory=list)


class EdgeSpec(BaseModel):
    """One semantic edge proposal from LLM output.

    Attributes:
        from: Source node reference (concept-tree id / depth-tree id
            ``d:{anchor}:{title}`` / cst id).
        to: Target node reference (same rules as ``from``).
        relation: Relation name; must be inside the closed vocabulary
            (validated by :func:`validate_relations` with injected vocab).
        rationale: LLM reasoning for this edge.
        confidence: One of "semantic" | "rule" | "structure".
    """

    from_: str = Field(alias="from")
    to: str
    relation: str
    rationale: str = ""
    confidence: str = "semantic"

    model_config = {"populate_by_name": True}


class OpenQuestions(BaseModel):
    """One world-building question derived from an out-of-vocabulary relation."""

    question: str


class GraphifyResult(BaseModel):
    """Aggregated SIR contract: the five fields of one graphify LLM call.

    Contract D4: every list/dict field defaults to empty (missing = empty,
    partial acceptance). ``success=False`` + ``warning`` signals degraded
    output; finalize must never block on LLM failure.
    """

    success: bool = True
    warning: str = ""
    module_summaries: dict[str, str] = Field(default_factory=dict)
    entries: list[AnchorEntries] = Field(default_factory=list)
    edges: list[EdgeSpec] = Field(default_factory=list)
    constraint_fields: dict[str, str] = Field(default_factory=dict)
    open_questions: list[OpenQuestions] = Field(default_factory=list)


# =============================================================================
# Title sanitization and depth-tree id helpers
# =============================================================================


def sanitize_title(title: str) -> str:
    """Normalize an LLM-provided title into an id-safe title.

    Rules:
        - remove all ``:`` characters (reserved for the id delimiter);
        - collapse any whitespace run into a single space;
        - strip and truncate to 32 characters;
        - if nothing remains, return the placeholder ``"未命名"``.
    """
    cleaned = _WHITESPACE_RE.sub(" ", title.replace(":", "")).strip()
    if not cleaned:
        return _UNNAMED_PLACEHOLDER
    return cleaned[:_TITLE_MAX_LEN]


def depth_id(anchor: str, title: str) -> str:
    """Mint a depth-tree node id ``d:{anchor}:{sanitized_title}``.

    ``anchor`` is a ``module.subfield`` key (contains ``.`` but never ``:``),
    so parsing back uses ``split(':', 2)`` — see :func:`parse_depth_id`.
    """
    return f"d:{anchor}:{sanitize_title(title)}"


def parse_depth_id(node_id: str) -> tuple[str, str]:
    """Parse ``d:{anchor}:{title}`` back into ``(anchor, title)``.

    Uses ``split(':', 2)`` because the anchor may contain ``.`` but never
    ``:``, while the sanitized title has no ``:`` either.

    Raises:
        ValueError: If the id does not start with ``d:`` or lacks the
            anchor/title parts.
    """
    if not node_id.startswith("d:"):
        raise ValueError(f"not a depth id: {node_id!r}")
    parts = node_id[2:].split(":", 2)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"malformed depth id: {node_id!r}")
    return parts[0], parts[1]


# =============================================================================
# Dedup helpers (same anchor + same title → keep first)
# =============================================================================


def dedupe_items(items: list[EntryItem]) -> tuple[list[EntryItem], list[str]]:
    """Drop duplicate titles within one anchor's item list, keeping first.

    Returns:
        ``(kept_items, duplicate_titles)`` — duplicates are reported so the
        caller can surface them as warnings (never silently dropped).
    """
    kept: list[EntryItem] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = sanitize_title(item.title)
        if key in seen:
            duplicates.append(item.title)
            continue
        seen.add(key)
        kept.append(item)
    return kept, duplicates


# =============================================================================
# Validation rules (four rules from contract §4; standalone functions —
# the assembler wiring happens in a later task)
# =============================================================================


def validate_anchors(result: GraphifyResult) -> list[str]:
    """Rule 1: every entry anchor must be a legal ``module.subfield`` key.

    Illegal anchors are reported (LLM must not invent anchors); the caller
    drops the offending group and surfaces the warning.
    """
    legal = set(all_subfield_keys())
    return [
        f"非法锚点: {group.anchor!r}"
        for group in result.entries
        if group.anchor not in legal
    ]


def validate_relations(
    edges: list[EdgeSpec], allowed_relations: set[str]
) -> list[str]:
    """Rule 3 (contract numbering): every relation must be in the closed vocab.

    ``allowed_relations`` is injected by the caller (must NOT be imported
    from concept_edge_vocab here — T2 edits that module in parallel).
    """
    return [
        f"词表外关系: {edge.relation!r} (from={edge.from_!r}, to={edge.to!r})"
        for edge in edges
        if edge.relation not in allowed_relations
    ]


def validate_constraint_fields(result: GraphifyResult) -> list[str]:
    """Rule 4: ``constraint_fields`` keys must be ``DIM.tag`` inside the
    STRUCTURED_FIELDS 21-field whitelist."""
    warnings: list[str] = []
    for key in result.constraint_fields:
        dim, _, tag = key.partition(".")
        if tag not in STRUCTURED_FIELDS.get(dim, []):
            warnings.append(f"约束字段不在白名单: {key!r}")
    return warnings


def validate_children_depth(result: GraphifyResult) -> list[str]:
    """Rule 5: ``children`` depth is closed in Phase 1.

    Returns warnings (never raises) for every group containing nested
    children; the caller flattens/drops them per partial-accept semantics.
    """
    warnings: list[str] = []
    for group in result.entries:
        for item in group.items:
            if item.children:
                warnings.append(
                    f"children 深度 Phase 1 不开放: {group.anchor} / {item.title!r}"
                )
    return warnings
