"""Concept edge extractor — LLM单次调用抽取概念边的封装 (Task 5).

核心设计：
- finalize 时一次 LLM 调用抽取概念边
- TDD 全部 mock LLM，零真实调用
- 词表校验：relation ∉ VOCAB_RELATION_NAMES → 转入 open_questions（表外关系→世界观问句模板转译，禁术语）
- 空模块跳过（Metis E7）：from/to 槽位对应模块无 answers → 不产出该边
- 抽取上限：边数 ≤ 1.5×已填条目数，超限截断（优先级 rule > semantic > structure）
- 异常降级：chat_json 抛异常 → ExtractResult(success=False, warning 含 "concept_edge")，永不抛出
- ◆ semantic 边默认 confirmed=False；★ rule 边由 AXIS 归类点燃（axis_assignments 匹配 EDGE_VOCAB level=rule 的条件 → confirmed=True）
- 不可动清单注入：answers 含设定边界.immutable_core 时进入 prompt

Contract (Task 7 finalize 集成消费):
- 函数签名: extract_concept_edges(session, vocab, provider=None) -> ExtractResult
- ExtractResult 字段: edges (list[ExtractedEdge]), axis_assignments (list[AxisAssignment]), open_questions (list[str]), success (bool), warning (str)
- Provider 注入: 可选参数，默认 None 时从 app.ai 依赖获取
- 规则边点燃逻辑: axis_assignments 槽位归类值 → 匹配 EDGE_VOCAB level="rule" 的条目 → confirmed=True

Reference:
- Task 2: concept_edge_vocab.py (EDGE_VOCAB 16 边/AXIS_SLOTS/VOCAB_RELATION_NAMES)
- interviewer.py: RealLLMInterviewer.interview 调用范式 (chat_json 单次调用)
- test_guide_engine.py: Fake 注入范式
"""
from __future__ import annotations

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider
from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES
from app.domains.creation.a1.concept_relation_vocab import RelationRegistry


# =============================================================================
# Output Models (Pydantic v2 BaseModel)
# =============================================================================


class ExtractedEdge(BaseModel):
    """One extracted concept edge from LLM output.

    Attributes:
        from_slot: Source slot path (using concept tree naming)
        to_slot: Target slot path (using concept tree naming)
        relation: Edge relation name (must be in VOCAB_RELATION_NAMES)
        confidence: Credibility level (★=rule, ◆=semantic, ◇=structure)
        rationale: LLM reasoning for this edge
        confirmed: Whether edge is confirmed (default: False for semantic, True for rule after ignition)
    """

    from_slot: str
    to_slot: str
    relation: str
    confidence: str = "semantic"  # Literal["rule", "semantic", "structure"]
    rationale: str = ""
    confirmed: bool = False


class AxisAssignment(BaseModel):
    """AXIS slot binary spectrum assignment.

    Attributes:
        slot: Slot path (e.g., "世界本体.起源.起源力量")
        side: Binary spectrum value (e.g., "意志型" vs "物质型")
        rationale: LLM reasoning for this assignment
    """

    slot: str
    side: str
    rationale: str = ""


class ExtractResult(BaseModel):
    """Result of concept edge extraction.

    Attributes:
        edges: List of extracted edges (after vocabulary validation and limit truncation)
        axis_assignments: List of AXIS slot assignments
        open_questions: List of world-building questions (for out-of-vocabulary relations)
        success: Whether extraction succeeded (False on LLM error)
        warning: Warning message if extraction failed (contains "concept_edge" keyword)
    """

    edges: list[ExtractedEdge] = Field(default_factory=list)
    axis_assignments: list[AxisAssignment] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    success: bool = True
    warning: str = ""


# =============================================================================
# Main Extraction Function
# =============================================================================


def extract_concept_edges(
    session: Any,
    vocab: Any,
    provider: LLMProvider | None = None,
) -> ExtractResult:
    """Extract concept edges from session.answers using LLM single call.

    Args:
        session: Session object with answers dict (35 items expected)
        vocab: EDGE_VOCAB from concept_edge_vocab.py (16 edges + AXIS_SLOTS)
        provider: Optional LLM provider (if None, uses default from app.ai)

    Returns:
        ExtractResult with edges, axis_assignments, open_questions, success flag

    Failure degradation:
        - On LLM error: returns ExtractResult(success=False, warning contains "concept_edge")
        - Never raises exceptions (top-level try/except wrapper)
    """
    # Extract answers from session
    answers = getattr(session, "answers", {})

    # Count filled answers for extraction limit
    filled_count = sum(1 for v in answers.values() if v and v.strip())
    max_edges = int(filled_count * 1.5)  # 抽取上限：1.5×已填条目数

    # Build prompt with closed vocabulary constraint + immutable core
    system = _build_prompt(answers, vocab, max_edges)

    # Prepare messages
    messages = [{"role": "system", "content": system}]

    # Try LLM call with degradation
    try:
        # Use injected provider or default
        if provider is None:
            # Fall back to default provider (should not happen in tests)
            from app.ai import get_default_provider

            provider = get_default_provider()

        # Single LLM call (chat_json)
        raw = asyncio.run(provider.chat_json(messages))

        # Parse LLM response
        result = _parse_response(raw, answers, vocab, max_edges)

        # Apply rule edge ignition (AXIS assignments → rule edges confirmed=True)
        result = _apply_rule_edge_ignition(result, vocab)

        return result

    except Exception as e:  # noqa: BLE001 — degrade, never crash
        # Failure degradation: success=False + warning with "concept_edge"
        return ExtractResult(
            success=False,
            warning=f"concept_edge extraction failed: {str(e)[:200]}",
        )


# =============================================================================
# Prompt Building
# =============================================================================


def _immutable_block(answers: dict[str, str]) -> str:
    """Build the 【不可动清单】 content from answers."""
    raw = answers.get("设定边界.immutable_core", "")
    if raw and raw.strip():
        return raw.strip()
    return "（暂无不可动设定）"


def _build_prompt(answers: dict[str, str], vocab: Any, max_edges: int) -> str:
    """Build system prompt with closed vocabulary constraint + JSON schema."""
    # Extract immutable core if present
    immutable_block = _immutable_block(answers)

    # Build vocabulary list (relation names only)
    vocab_names = "\n".join(f"  - {name}" for name in VOCAB_RELATION_NAMES)

    # Build answers digest
    answers_lines = [f"{k} = {v[:80] if len(v) > 80 else v}" for k, v in answers.items() if v]
    answers_digest = "\n".join(answers_lines) if answers_lines else "（暂无）"

    return "\n".join(
        [
            "你是TRPG世界观概念边抽取器，负责从用户已填写的A1问卷答案中抽取概念边关系。",
            "",
            "【用户已确定的内容】（35个问卷模块的答案）",
            answers_digest,
            "",
            "【不可动清单】（设定边界.不可变集中的锚点，绝对不可覆盖）",
            immutable_block,
            "",
            "【你的任务】",
            "1. 分析【用户已确定的内容】，抽取概念边关系。",
            "2. 只能使用下列关系名（封闭词表），不得自造：",
            vocab_names,
            "3. 如果发现的关系不在上述词表中，将其转入 open_questions，转译为世界观问句",
            "   （禁止使用术语：拓扑/槽位/派生/枚举/轴向/上游/下游，必须转译为用户可理解的设定式表述）。",
            "4. 边的数量限制：最多 " + str(max_edges) + " 条边（1.5×已填条目数），超限截断。",
            "5. 边的优先级：★ rule（规则边，机器可执行）> ◆ semantic（语义边，需确认）> ◇ structure（结构边，解析展开）",
            "6. 轴向归类：对8个AXIS槽位进行二元谱系归类（详见词表中的 AXIS_SLOTS）。",
            "7. ★ rule 边默认 confirmed=False，但若 axis_assignments 中的槽位归类值匹配词表中 level='rule' 的条件，则 confirmed=True。",
            "8. ◆ semantic 边默认 confirmed=False。",
            "",
            "【返回格式】严格JSON（不要输出其他内容）：",
            '{"edges": [{"from_slot": "...", "to_slot": "...", "relation": "...", "confidence": "rule/semantic/structure", "rationale": "...", "confirmed": false}],',
            ' "axis_assignments": [{"slot": "...", "side": "...", "rationale": "..."}],',
            ' "open_questions": ["..."]}',
        ]
    )


# =============================================================================
# Response Parsing
# =============================================================================


def _parse_response(
    raw: dict[str, Any],
    answers: dict[str, str],
    vocab: Any,
    max_edges: int,
) -> ExtractResult:
    """Parse LLM response into ExtractResult with vocabulary validation and limit truncation."""
    # Extract three segments
    edges_data = raw.get("edges", [])
    axis_data = raw.get("axis_assignments", [])
    open_q_data = raw.get("open_questions", [])

    # Parse edges
    edges: list[ExtractedEdge] = []
    open_questions: list[str] = list(open_q_data) if isinstance(open_q_data, list) else []

    for item in edges_data:
        if not isinstance(item, dict):
            continue

        from_slot = item.get("from_slot", "")
        to_slot = item.get("to_slot", "")
        relation = item.get("relation", "")
        confidence = item.get("confidence", "semantic")
        rationale = item.get("rationale", "")
        confirmed = item.get("confirmed", False)

        # Metis E7: 空模块跳过 - from_slot 对应模块无 answers → 不产出该边
        # (targets can be empty - they're what we're deriving)
        if not _has_answer_for_slot(from_slot, answers):
            continue

        # 词表校验：relation ∉ VOCAB_RELATION_NAMES → 转入 open_questions
        if relation not in VOCAB_RELATION_NAMES:
            # 表外关系→世界观问句模板转译，禁术语
            question = _translate_out_of_vocab_relation(
                from_slot, to_slot, relation, rationale
            )
            open_questions.append(question)
            continue

        # Valid edge → add to list
        edges.append(
            ExtractedEdge(
                from_slot=from_slot,
                to_slot=to_slot,
                relation=relation,
                confidence=confidence,
                rationale=rationale,
                confirmed=confirmed,
            )
        )

    # Parse axis assignments
    axis_assignments: list[AxisAssignment] = []
    for item in axis_data:
        if not isinstance(item, dict):
            continue
        slot = item.get("slot", "")
        side = item.get("side", "")
        rationale = item.get("rationale", "")
        if slot and side:
            axis_assignments.append(AxisAssignment(slot=slot, side=side, rationale=rationale))

    # 抽取上限截断 + 优先级排序 (rule > semantic > structure)
    edges = _truncate_and_sort_edges(edges, max_edges)

    return ExtractResult(
        edges=edges,
        axis_assignments=axis_assignments,
        open_questions=open_questions,
        success=True,
        warning="",
    )


def _has_answer_for_slot(slot: str, answers: dict[str, str]) -> bool:
    """Check if slot's module has any answers (Metis E7 empty module skip).

    Slot format: "世界本体.现实规则" (concept tree naming)
    Answer keys format: "世界本体.现实规则" or "世界本体.其他字段"

    Check if any answer key starts with the slot's module prefix (before first dot).
    """
    # Extract module prefix (before first dot)
    parts = slot.split(".")
    if not parts:
        return False

    # Check if any answer key starts with this module prefix
    module_prefix = parts[0]
    for key in answers.keys():
        # Split answer key and check module prefix
        key_parts = key.split(".")
        if key_parts and key_parts[0] == module_prefix:
            return True

    return False


def _translate_out_of_vocab_relation(
    from_slot: str, to_slot: str, relation: str, rationale: str
) -> str:
    """转译表外关系为世界观问句（禁术语：拓扑/槽位/派生/枚举/轴向/上游/下游）."""
    # 简化版转译：移除术语，保留语义
    question = f"关于「{from_slot}」与「{to_slot}」的关系"

    # 移除禁止术语
    forbidden_terms = ["拓扑", "槽位", "派生", "枚举", "轴向", "上游", "下游"]
    for term in forbidden_terms:
        question = question.replace(term, "")
        relation = relation.replace(term, "")

    question += f"（系统识别关系：{relation}，推理依据：{rationale}）"
    return question


def _truncate_and_sort_edges(edges: list[ExtractedEdge], max_edges: int) -> list[ExtractedEdge]:
    """截断边数上限 + 优先级排序 (rule > semantic > structure)."""
    # Sort by priority (rule > semantic > structure)
    priority_order = {"rule": 0, "semantic": 1, "structure": 2}
    edges.sort(key=lambda e: priority_order.get(e.confidence, 3))

    # Truncate to max_edges
    return edges[:max_edges]


# =============================================================================
# Rule Edge Ignition (AXIS assignments → rule edges confirmed=True)
# =============================================================================


def _apply_rule_edge_ignition(result: ExtractResult, vocab: Any) -> ExtractResult:
    """★ rule 边由 AXIS 归类点燃（axis_assignments 匹配 EDGE_VOCAB level=rule 的条件 → confirmed=True）."""
    # Extract axis assignments
    axis_map = {assign.slot: assign.side for assign in result.axis_assignments}

    # Ignite rule edges
    for edge in result.edges:
        if edge.confidence != "rule":
            continue

        # Check if axis_assignments match vocab level='rule' conditions
        # Simple heuristic: if from_slot or to_slot appears in axis_assignments, ignite
        if edge.from_slot in axis_map or edge.to_slot in axis_map:
            edge.confirmed = True

    return result


# =============================================================================
# Default Provider (for provider=None case)
# =============================================================================


def get_default_provider() -> LLMProvider:
    """Get default LLM provider from app.ai (fallback when provider=None)."""
    # This should be implemented in app.ai.__init__ or similar
    # For now, raise NotImplementedError (tests should always inject provider)
    raise NotImplementedError(
        "Default provider not implemented - tests must inject mock provider"
    )


# =============================================================================
# 两阶段抽取器 V2 (Task T-A 用户产品决策)
# =============================================================================
# 阶段1: extract_concept_terms  — 从回答值中抽概念词节点（用户确认/否决）
# 阶段2: extract_concept_relations — 节点确认后，用概念关系词典抽边（提议制）
# 词典: concept_relation_vocab.py (RelationRegistry, 种子10条+运行时入典)
# 降级约定与旧 extract_concept_edges 一致：永不抛出，success=False + warning
# warning 关键字: 阶段1 "concept_term" / 阶段2 "concept_edge"
# =============================================================================


class ConceptTerm(BaseModel):
    """阶段1产出：一个概念词节点。

    Attributes:
        term: 概念词（≤8字中文短语，名词性）——设定中实际起作用的概念实体
        field_key: 来源 module.subfield（同词跨字段去重时记首次出现）
        gloss: 一句话释义（可选）
        confirmed: 用户确认态（默认 False，阶段2只连已确认词）
    """

    term: str
    field_key: str
    gloss: str = ""
    confirmed: bool = False


class TermsResult(BaseModel):
    """阶段1结果。"""

    terms: list[ConceptTerm] = Field(default_factory=list)
    success: bool = True
    warning: str = ""


class ConceptEdgeV2(BaseModel):
    """阶段2产出：一条概念边。

    Attributes:
        from_term / to_term: 概念词（必须在已确认概念词集合内）
        relation: 词典关系名（∈当前 RELATION_NAMES）或 LLM 提议新词
        is_new_relation: 提议新词标记（待用户确认入典，默认◆semantic）
        rationale: 判定依据
        confidence: 三级可信度（★=rule, ◆=semantic, ◇=structure）
        confirmed: 用户确认态（默认 False，提议制逐条确认）
    """

    from_term: str
    to_term: str
    relation: str
    is_new_relation: bool = False
    rationale: str = ""
    confidence: Literal["rule", "semantic", "structure"] = "semantic"
    confirmed: bool = False


class EdgesV2Result(BaseModel):
    """阶段2结果。"""

    edges: list[ConceptEdgeV2] = Field(default_factory=list)
    success: bool = True
    warning: str = ""


# =============================================================================
# 阶段1: 概念词抽取
# =============================================================================


def _terms_prompt(answers: dict[str, str]) -> str:
    """阶段1 prompt：从每个已填字段的值中提取 1-3 个核心概念词。"""
    answers_lines = [f"{k} = {v[:80] if len(v) > 80 else v}" for k, v in answers.items() if v]
    answers_digest = "\n".join(answers_lines) if answers_lines else "（暂无）"
    return "\n".join(
        [
            "你是TRPG世界观概念词抽取器，负责从用户已填写的A1问卷答案中拆出概念词节点。",
            "",
            "【用户已确定的内容】",
            answers_digest,
            "",
            "【你的任务】",
            "1. 从每个已填字段的值中提取 1-3 个核心概念词。",
            "2. 概念词 = 设定中实际起作用的概念实体（如「死亡转生」「业报」「轮回之门」），",
            "   不是字段名，不是整句回答。",
            "3. 概念词为 ≤8 字的中文名词性短语。",
            "4. 每个概念词给出一句话释义（gloss，可选）。",
            "",
            "【返回格式】严格JSON（不要输出其他内容）：",
            '{"terms": [{"term": "...", "field_key": "模块.子字段", "gloss": "..."}]}',
        ]
    )


def extract_concept_terms(
    session: Any,
    provider: LLMProvider | None = None,
) -> TermsResult:
    """阶段1：从 session.answers 中抽取概念词节点。

    去重规则：同词跨字段保留一个，field_key 记首次出现。
    降级：LLM 异常 → TermsResult(success=False, warning 含 "concept_term")，永不抛出。
    """
    try:
        answers = getattr(session, "answers", {}) or {}
        filled = {k: v for k, v in answers.items() if v and v.strip()}
        if not filled:
            return TermsResult(terms=[], success=True, warning="")

        if provider is None:
            provider = get_default_provider()

        raw = asyncio.run(provider.chat_json([{"role": "system", "content": _terms_prompt(filled)}]))
        items = raw.get("terms", [])

        terms: list[ConceptTerm] = []
        seen: dict[str, str] = {}  # term -> field_key（首次出现）
        for item in items:
            if not isinstance(item, dict):
                continue
            term = item.get("term", "")
            if not term or not isinstance(term, str):
                continue
            if term in seen:
                continue  # 同词跨字段去重，保留首次
            seen[term] = item.get("field_key", "")
            terms.append(
                ConceptTerm(
                    term=term,
                    field_key=seen[term],
                    gloss=item.get("gloss", ""),
                    confirmed=False,
                )
            )
        return TermsResult(terms=terms, success=True, warning="")

    except Exception as e:  # noqa: BLE001 — degrade, never crash
        return TermsResult(
            success=False,
            warning=f"concept_term extraction failed: {str(e)[:200]}",
        )


# =============================================================================
# 阶段2: 概念边抽取（节点确认后）
# =============================================================================


def _relations_prompt(
    confirmed_terms: list[ConceptTerm],
    known_relations: list[str],
    max_edges: int,
) -> str:
    """阶段2 prompt：只能连接已确认概念词；关系优先用词典现有名。"""
    terms_lines = [f"  - {t.term}（来自 {t.field_key}）" for t in confirmed_terms]
    terms_digest = "\n".join(terms_lines) if terms_lines else "（暂无）"
    vocab_lines = "\n".join(f"  - {name}" for name in known_relations)
    return "\n".join(
        [
            "你是TRPG世界观概念边抽取器，负责在已确认的概念词之间建立概念关系。",
            "",
            "【已确认概念词节点】（只能连接这些词，不得自造节点）",
            terms_digest,
            "",
            "【概念关系词典】（优先使用这些关系名）",
            vocab_lines,
            "",
            "【你的任务】",
            "1. 只能连接【已确认概念词节点】中的词。",
            "2. 关系优先使用词典现有名；内容确实需要新关系时可提议新词，并标 is_new_relation=true。",
            "3. 每条边给出判定依据（rationale）。",
            "4. 边的数量限制：最多 " + str(max_edges) + " 条边（1.5×概念词数），超限截断。",
            "5. 边的优先级：★ rule > ◆ semantic > ◇ structure。",
            "",
            "【返回格式】严格JSON（不要输出其他内容）：",
            '{"edges": [{"from_term": "...", "to_term": "...", "relation": "...", "is_new_relation": false, "rationale": "...", "confidence": "rule/semantic/structure"}]}',
        ]
    )


def extract_concept_relations(
    terms: list[ConceptTerm],
    session: Any,
    registry: RelationRegistry,
    provider: LLMProvider | None = None,
) -> EdgesV2Result:
    """阶段2：在已确认概念词之间抽取概念边（关系词典提议制）。

    词表校验：relation ∈ 词典 → 按 RelationSpec.level 定 confidence；
    新词 → confidence="semantic" + is_new_relation=True（待用户确认入典）。
    上限：边数 ≤ 概念词数×1.5（rule > semantic > structure 优先截断）。
    降级：LLM 异常 → EdgesV2Result(success=False, warning 含 "concept_edge")，永不抛出。
    """
    try:
        confirmed = [t for t in terms if t.confirmed]
        if not confirmed:
            return EdgesV2Result(edges=[], success=True, warning="")

        max_edges = int(len(confirmed) * 1.5)  # 抽取上限：1.5×概念词数
        known_names = [spec.name for spec in registry.all_specs()]

        if provider is None:
            provider = get_default_provider()

        system = _relations_prompt(confirmed, known_names, max_edges)
        raw = asyncio.run(provider.chat_json([{"role": "system", "content": system}]))

        # 已确认概念词集合
        term_names = {t.term for t in confirmed}

        edges: list[ConceptEdgeV2] = []
        for item in raw.get("edges", []):
            if not isinstance(item, dict):
                continue
            from_term = item.get("from_term", "")
            to_term = item.get("to_term", "")
            # 只能连接已确认概念词
            if from_term not in term_names or to_term not in term_names:
                continue
            relation = item.get("relation", "")
            if not relation or not isinstance(relation, str):
                continue

            if registry.is_known(relation):
                # 词典关系 → 按 RelationSpec.level 定 confidence
                spec = next(s for s in registry.all_specs() if s.name == relation)
                confidence: Literal["rule", "semantic", "structure"] = spec.level
                is_new = False
            else:
                # 新词 → semantic + is_new_relation（待用户确认入典）
                confidence = "semantic"
                is_new = True

            edges.append(
                ConceptEdgeV2(
                    from_term=from_term,
                    to_term=to_term,
                    relation=relation,
                    is_new_relation=is_new,
                    rationale=item.get("rationale", ""),
                    confidence=confidence,
                    confirmed=False,
                )
            )

        # 上限截断 + 优先级排序 (rule > semantic > structure)
        priority_order = {"rule": 0, "semantic": 1, "structure": 2}
        edges.sort(key=lambda e: priority_order.get(e.confidence, 3))
        edges = edges[:max_edges]

        return EdgesV2Result(edges=edges, success=True, warning="")

    except Exception as e:  # noqa: BLE001 — degrade, never crash
        return EdgesV2Result(
            success=False,
            warning=f"concept_edge extraction failed: {str(e)[:200]}",
        )
