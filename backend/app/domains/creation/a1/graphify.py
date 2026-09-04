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

import asyncio
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES
from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.tier_map import TIER_MAP
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

# =============================================================================
# graphify_llm — one-shot LLM graphification (T6)
# =============================================================================


def _answers_block(answers: dict[str, str]) -> str:
    """Full-text answers block (NL contract C1: verbatim, no truncation)."""
    lines = [f"{k} = {v}" for k, v in answers.items() if v]
    return "\n".join(lines) if lines else "（暂无）"


def _immutable_block(answers: dict[str, str]) -> str:
    """【不可动清单】content from 设定边界.immutable_core answer."""
    raw = answers.get("设定边界.immutable_core", "")
    if raw and raw.strip():
        return raw.strip()
    return "（暂无不可动设定）"


def _tier_block() -> str:
    """Static tier mapping table (contract §3, closed 10-module coverage)."""
    return "\n".join(f"  - {mid} → tier {tier}" for mid, tier in TIER_MAP.items())


def _vocab_block() -> str:
    """Closed relation vocabulary (26 edges; LLM must not invent names)."""
    return "\n".join(f"  - {name}" for name in sorted(VOCAB_RELATION_NAMES))


def _evidence_block(answered_evidence: list[str] | None) -> str:
    """C7 promotion-evidence block (T17 wires this; empty slot for now)."""
    if not answered_evidence:
        return "（暂无上一轮已回答的转正证据）"
    return "\n".join(f"  - {q}" for q in answered_evidence)


def build_graphify_prompt(
    answers: dict[str, str],
    answered_evidence: list[str] | None = None,
) -> str:
    """Build the graphify system prompt (governance doc §4 input contract).

    Blocks: answers full text / closed vocab (26) / immutable list /
    tier mapping table / node reference rules (``d:{anchor}:{title}`` /
    C7 answered-evidence slot.
    """
    return "\n".join(
        [
            "你是TRPG世界观图谱化引擎，负责把用户已确定的问卷答案做一次性的"
            "结构化+关系化（模块归纳、条目提取、关系建立、约束归类）。",
            "",
            "【用户已确定的内容】（问卷答案全文）",
            _answers_block(answers),
            "",
            "【不可动清单】（设定边界.immutable_core 的内容，绝对不可覆盖）",
            _immutable_block(answers),
            "",
            "【上一轮已回答的转正证据】（回答过的开放问题，可作为关系成立的依据）",
            _evidence_block(answered_evidence),
            "",
            "【关系封闭词表】（只能使用下列关系名，不得自造任何词表外关系）：",
            _vocab_block(),
            "",
            "【模块层级映射表】（10个模块的语义层级，封闭）：",
            _tier_block(),
            "",
            "【节点引用规则】",
            "1. 深度树条目节点 id 用内容锚定编码：d:{锚点}:{条目标题}，",
            "   例如 d:力量体系.acquire:斗气分裂。锚点必须是合法的 模块.子字段 键。",
            "2. 概念树节点直接引用 模块id 或 模块id.子字段id。",
            "3. 约束节点 id 格式：cst_{DIM}_{tag}，DIM.tag 必须在白名单内。",
            "4. 边的 from/to 只能引用上述三类节点，不得引用不存在的节点。",
            "",
            "【你的任务】",
            "1. module_summaries：每个已填模块给一句话归纳（不超过40字）。",
            "2. entries：从答案中提取内容条目，anchor 必须是合法的 模块.子字段 键；",
            "   同级条目并列放 items；Phase 1 不开放嵌套，children 必须为空。",
            "3. edges：只使用封闭词表内的关系名；confidence 取 semantic/rule/structure。",
            "   若发现词表外的关系，不要放进 edges，转译为世界观问句放进 open_questions",
            "   （禁止使用拓扑/槽位/派生等术语，用用户可理解的设定式表述）。",
            "4. constraint_fields：把可归类为约束的内容按 DIM.tag 白名单归类。",
            "5. open_questions：词表外关系、悬而未决的设定问题，转译为问句。",
            "",
            "【返回格式】严格JSON（不要输出其他内容）：",
            '{"module_summaries": {"<模块id>": "一句话归纳"},',
            ' "entries": [{"anchor": "<模块.子字段>", "items": [{"title": "…", "content": "…", "children": []}]}],',
            ' "edges": [{"from": "<节点引用>", "to": "<节点引用>", "relation": "<词表内关系名>", "rationale": "…", "confidence": "semantic"}],',
            ' "constraint_fields": {"<DIM>.<tag>": "<值>"},',
            ' "open_questions": ["世界观问句"]}',
        ]
    )


# ---------- raw dict → GraphifyResult (D4: missing = empty; wrong type = fail) ----------


def _require_dict(raw: dict[str, Any], key: str) -> dict[str, Any]:
    val = raw.get(key)
    if val is None:
        return {}
    if not isinstance(val, dict):
        raise ValueError(f"{key} 应为对象，实际为 {type(val).__name__}")
    return val


def _require_list(raw: dict[str, Any], key: str) -> list[Any]:
    val = raw.get(key)
    if val is None:
        return []
    if not isinstance(val, list):
        raise ValueError(f"{key} 应为列表，实际为 {type(val).__name__}")
    return val


def parse_graphify_raw(raw: Any) -> GraphifyResult:
    """Parse the raw LLM dict into a GraphifyResult.

    D4 partial acceptance: missing list/dict fields default to empty.
    Wrong container type (list where dict expected etc.) raises — the
    caller treats that as a total failure (degrade, never crash).
    """
    if not isinstance(raw, dict):
        raise ValueError("graphify 输出不是 JSON 对象")
    return GraphifyResult(
        module_summaries={
            str(k): str(v) for k, v in _require_dict(raw, "module_summaries").items()
        },
        entries=[
            AnchorEntries.model_validate(item) for item in _require_list(raw, "entries")
        ],
        edges=[EdgeSpec.model_validate(item) for item in _require_list(raw, "edges")],
        constraint_fields={
            str(k): str(v) for k, v in _require_dict(raw, "constraint_fields").items()
        },
        open_questions=[
            OpenQuestions.model_validate(item)
            if isinstance(item, dict)
            else OpenQuestions(question=str(item))
            for item in _require_list(raw, "open_questions")
        ],
    )


# ---------- post-parse validation interception (contract §4 rules 1-5) ----------


def _endpoint_exists(endpoint: str, result: GraphifyResult) -> bool:
    """Contract rule 2: edge endpoints must reference real node ids.

    Accepts: concept-tree ids (module id / module.subfield key),
    depth-tree ids (``d:{anchor}:{title}`` minted this round),
    cst ids (``cst_{DIM}_{tag}`` in the whitelist).
    """
    if endpoint.startswith("d:"):
        try:
            anchor, title = parse_depth_id(endpoint)
        except ValueError:
            return False
        if anchor not in set(all_subfield_keys()):
            return False
        known = {
            sanitize_title(item.title)
            for group in result.entries
            if group.anchor == anchor
            for item in group.items
        }
        return title in known
    if endpoint.startswith("cst_"):
        rest = endpoint[len("cst_") :]
        dim, _, tag = rest.partition("_")
        return tag in STRUCTURED_FIELDS.get(dim, [])
    # concept-tree id: module id or module.subfield key
    if endpoint in TIER_MAP:
        return True
    return endpoint in set(all_subfield_keys())


def apply_graphify_validation(result: GraphifyResult) -> GraphifyResult:
    """In-place validation interception; returns the same result mutated.

    - illegal anchor → drop the group + ``[entries]`` warning (rule 1)
    - out-of-vocab relation → edge removed, question moved to
      open_questions + ``[edges]`` warning (rule 3)
    - DIM.tag off the whitelist → key dropped + ``[constraint_fields]``
      warning (rule 4)
    - non-empty children → warning only, Phase 1 keeps items (rule 5)
    - hallucinated node reference → edge dropped + ``[edges]`` warning
      (rule 2)

    Never raises.
    """
    warnings: list[str] = []

    # rule 1: illegal anchors dropped
    legal_anchors = set(all_subfield_keys())
    kept_groups: list[AnchorEntries] = []
    for group in result.entries:
        if group.anchor in legal_anchors:
            kept_groups.append(group)
        else:
            warnings.append(f"[entries] 非法锚点已丢弃: {group.anchor!r}")
    result.entries = kept_groups

    # rule 3: out-of-vocab relation → open_questions
    kept_edges: list[EdgeSpec] = []
    for edge in result.edges:
        if edge.relation in VOCAB_RELATION_NAMES:
            kept_edges.append(edge)
        else:
            result.open_questions.append(
                OpenQuestions(
                    question=(
                        f"「{edge.from_}」与「{edge.to}」之间是否存在"
                        f"「{edge.relation}」这样的关系？请用世界观设定描述。"
                    )
                )
            )
            warnings.append(f"[edges] 词表外关系已转为开放问题: {edge.relation!r}")
    result.edges = kept_edges

    # rule 2: hallucinated node references dropped
    real_edges: list[EdgeSpec] = []
    for edge in result.edges:
        if _endpoint_exists(edge.from_, result) and _endpoint_exists(edge.to, result):
            real_edges.append(edge)
        else:
            warnings.append(
                f"[edges] 引用了不存在的节点，边已丢弃: {edge.from_!r} → {edge.to!r}"
            )
    result.edges = real_edges

    # rule 4: DIM.tag whitelist
    for key in list(result.constraint_fields):
        dim, _, tag = key.partition(".")
        if tag not in STRUCTURED_FIELDS.get(dim, []):
            del result.constraint_fields[key]
            warnings.append(f"[constraint_fields] 约束字段不在白名单，已丢弃: {key!r}")

    # rule 5: children closed in Phase 1 (warning only, items kept)
    warnings.extend(validate_children_depth(result))

    if warnings:
        result.warning = (
            (result.warning + " | " if result.warning else "") + "；".join(warnings)
        )
    return result


def graphify_llm(
    session: Any,
    provider: Any,
    *,
    answered_evidence: list[str] | None = None,
    timeout: float | None = None,
) -> GraphifyResult:
    """One-shot LLM graphification (governance doc §4-§5).

    Contract: prompt = answers full text + closed vocab + immutable list +
    tier table + node reference rules (+ C7 answered evidence slot, wired
    in T17). Single ``chat_json`` call under ``asyncio.wait_for``; any
    failure (exception / timeout / parse error / validation shape error)
    degrades to ``GraphifyResult(success=False, warning="graphify failed: …")``
    and NEVER raises.

    Args:
        session: session object with ``answers: dict[str, str]``.
        provider: LLM provider exposing ``chat_json(messages)``.
        answered_evidence: C7 promotion evidence (T17 wiring; may be None).
        timeout: override ``GRAPHIFY_TIMEOUT`` (tests monkeypatch or inject).
    """
    session_id = getattr(session, "session_id", "unknown")
    effective_timeout = GRAPHIFY_TIMEOUT if timeout is None else timeout
    try:
        answers = getattr(session, "answers", {}) or {}
        system = build_graphify_prompt(answers, answered_evidence)
        messages = [{"role": "system", "content": system}]
        raw = asyncio.run(
            asyncio.wait_for(provider.chat_json(messages), timeout=effective_timeout)
        )
        log_event(session_id, "graphify_raw", chars=len(str(raw)))
        result = parse_graphify_raw(raw)
        return apply_graphify_validation(result)
    except Exception as e:  # noqa: BLE001 — degrade, never crash finalize
        warning = f"graphify failed: {str(e)[:200]}"
        log_event(session_id, "graphify_degraded", error=warning)
        return GraphifyResult(success=False, warning=warning)
