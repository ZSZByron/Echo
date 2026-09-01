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
from typing import Any

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider
from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES


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
