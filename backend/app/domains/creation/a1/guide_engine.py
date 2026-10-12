"""A1 guide engine — LLM-guided interview state machine.

Philosophy (2026-08-24 redesign):
    The question tree is a PROGRESS FRAMEWORK, not a form. The user
    speaks freely; the injected Interviewer (LLM) understands the input
    and fills the structured file — possibly several subfields at once.
    The engine then jumps to the first unanswered subfield. Only
    content the LLM judges to be outside the 10-module taxonomy enters
    the innovation-confirmation flow. When the LLM is unavailable the
    user is asked to retry — nothing is ever recorded without LLM
    judgment (blind-recording fix, 2026-08-26).

State: (current_module, current_subfield) tracks the first unanswered
subfield. Phase becomes 'completed' when every subfield across every
module has been answered or skipped.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1 import draft_version, graph_digest
from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.interviewer import (
    Interviewer,
    InterviewFill,
    Proposal,
)
from app.domains.creation.a1.open_questions import OpenQuestion
from app.domains.creation.seed.a1_question_tree import (
    ANSWER_MAX_CHARS,
    all_subfield_keys,
    clip_answer,
    first_module,
    first_subfield,
    get_module,
    get_subfield,
    is_finalizable,
    is_module_over_half,
    is_truthy_answer,
    module_ids,
    subs_for_module,
)
from app.domains.creation.seed.story_modules import (
    LIST_CAPS,
    THREE_TIER_TREE,
    VS_DIM_DIR,
    VS_DUAL,
    VS_FROM_TO,
    VS_POINT,
)
from app.domains.creation.shared.module_registry import (
    ANCHOR_BY_TYPE,  # noqa: F401 — E1-Lite 数据已迁入注册表，原位置 re-export 兼容
    MODULE_POOL,
    RECIPES,
    TYPE_ENTRY_SUBFIELD,  # noqa: F401 — 同上（消费侧改为查 Recipe.entry_subfield）
    TYPE_MODULE_PRIORITY,  # noqa: F401 — 同上
    resolve_recipe_id,
)
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    Suggestion,
)

PHASE_ASKING = "asking"
PHASE_COMPLETED = "completed"

# M0 止血：偏转占位答案（已逐字加入 a1_question_tree._PLACEHOLDER_ANSWERS
# 语义覆盖——J1 真值闸判非真值 → 门禁/进度不计数）。
DEFLECT_PLACEHOLDER = "（用户跳过）"

# ---------------------------------------------------------------------------
# M4a field_sources（impulse spec §6，D12 冻结设计）——人工/AI 作答溯源。
# 平行元数据：answers 旁的同键空间 dict[str, str]，绝不改写答案值本身。
# 四来源闭集（逐字锁定，不允许扩张）；只看不判：M4a 无任何行为分支消费
# 此元数据（门禁/进度/路由零改变，TestObserveOnly 契约锚定）。
FIELD_SOURCE_HUMAN = "human"                # 用户口述（当前问题的直接回答）
FIELD_SOURCE_LLM_FILL = "llm_fill"          # 访谈 fills 通道（已经用户 confirm）
FIELD_SOURCE_DICE_REC = "dice_rec"          # 骰子推荐写入
FIELD_SOURCE_UPLOAD_PREFILL = "upload_prefill"  # 上传预填（parse_modules 链）
FIELD_SOURCES: frozenset[str] = frozenset({
    FIELD_SOURCE_HUMAN,
    FIELD_SOURCE_LLM_FILL,
    FIELD_SOURCE_DICE_REC,
    FIELD_SOURCE_UPLOAD_PREFILL,
})


def mark_field_source(session: A1Session, key: str, source: str) -> None:
    """Tag one answer key with its write source (auto-mark, 都标自动标).

    Raises ValueError on a source outside the closed enum — a typo must
    fail loud at the write site, not silently pollute the metadata.
    """
    if source not in FIELD_SOURCES:
        raise ValueError(f"unknown field source: {source!r}")
    session.field_sources[key] = source


def apply_dice_recommendation(
    session: A1Session, key: str, value: str
) -> bool:
    """Outlet 4：骰子推荐按钮写入（确定性 apply 函数即单点接线）。

    J1 真值闸：占位值/空串不写入、不标记（与 _apply_fills 同一闸口径）。
    Returns True when written (and marked dice_rec), False otherwise.
    当前无 live 端点消费此函数（spec §6 骰子推荐按钮属 E1 前移）——
    M4a 只落接线点与标记，零行为变化。
    """
    if not is_truthy_answer(value):
        return False
    fill_value, was_clipped = clip_answer(value)
    if was_clipped:
        session.answer_clips.append(
            f"答案超{ANSWER_MAX_CHARS}字已截断: {key}（骰子推荐，原 {len(value)} 字）"
        )
    session.answers[key] = fill_value
    mark_field_source(session, key, FIELD_SOURCE_DICE_REC)
    return True


def _session_recipe_modules(session: A1Session) -> list[str]:
    """Resolve the session's ordered recipe module ids (M1 registry lookup).

    recipe_modules 非空（start_session 落定）→ 配方序（故事型=子集序）。
    存量会话（空，G3）→ E1-Lite 原路径逐字节复刻：creator_primary 查
    TYPE_MODULE_PRIORITY 做 head+rest 纯置换（保全集）；无/未知 profile →
    问卷树原序。确定性查表，LLM 不进控制流。
    """
    if session.recipe_modules:
        return list(session.recipe_modules)
    priority = TYPE_MODULE_PRIORITY.get(session.creator_primary or "")
    if not priority:
        return module_ids()
    return list(priority) + [mid for mid in module_ids() if mid not in priority]


def _session_entry_subfield(session: A1Session) -> tuple[str, str]:
    """Entry subfield swap for the session's recipe (default: ("", ""))."""
    if session.recipe_modules:
        recipe = RECIPES.get(session.recipe_id)
        if recipe is not None and recipe.entry_subfield:
            return recipe.entry_subfield
        return ("", "")
    return TYPE_ENTRY_SUBFIELD.get(session.creator_primary or "", ("", ""))


def _type_ordered_modules(session: A1Session) -> list[str]:
    """Recipe-driven module order (M1 registry; supersedes E1-Lite permutation).

    会话已落定配方（recipe_modules 非空）→ 配方序（故事型=子集序）。
    存量会话（无配方字段）→ creator_primary 查表：非故事型=纯置换
    （head+rest 保全集，与 E1-Lite 行为等价）；故事型=子集序（DN6 初稿）。
    无 profile / 未知值 → 问卷树原序（default 全集，G3 兼容）。
    """
    return _session_recipe_modules(session)


def apply_recipe_switch(session: A1Session, target_impulse: str) -> str:
    """D21⑦ 主次配方结合切换：联合边界内未访序调整（spec §5.4 L67）。

    - 边界不变：只重排 ``session.recipe_modules``（主∪次联合边界），
      不增不删（R6 forward-only）——已答字段被 ``sync_position`` 依
      answers 跳过，已访进度保留不重问；未访模块按 target 配方前移。
    - 新序 = target 配方 module_ids（∩联合边界）+ 其余模块按原序
      （invited_modules 天然留在"其余"段——D20 契约：切换不清零受邀
      模块、不重置其进度）。
    - target 闭集校验：仅接受本会话 creator_primary / creator_secondary；
      default/存量会话（recipe_modules 空）→ no-op。
    返回实际生效的 target impulse id（no-op 时返回 ""，调用方定 4xx）。
    """
    joint = list(session.recipe_modules)
    if not joint:
        return ""
    if target_impulse not in (session.creator_primary, session.creator_secondary):
        return ""
    recipe = RECIPES.get(resolve_recipe_id(target_impulse))
    if recipe is None:
        return ""
    head = [mid for mid in recipe.module_ids if mid in joint]
    rest = [mid for mid in joint if mid not in recipe.module_ids]
    session.recipe_modules = head + rest
    sync_position(session)
    return target_impulse


def _initial_subfield() -> str:
    """Return the id of the first subfield of the first module."""
    m = first_module()
    sf = first_subfield(m["id"])
    return sf["id"]


class AnswerNode(BaseModel):
    """D23 层级答案条目：多值字段的树形承载（G3 零迁移——存量 str 答案
    读取时按需晋升，落库形态仍以 answer_view 渲染为单串）。"""

    text: str = ""
    children: list[AnswerNode] = Field(default_factory=list)
    source: str = ""


def answer_view(value: str | AnswerNode | dict[str, Any]) -> str:
    """C11 渲染确定性：str 直通；node = 非空片段按深度优先序「；」连接；
    dict（批B 结构化值）= 叶值深度优先「；」连接（additive——str/node
    行为逐字节不变）。渲染纯函数（同输入同输出，无状态）；空片段跳过。
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _l3_render(value)
    parts: list[str] = []
    if value.text.strip():
        parts.append(value.text)
    for child in value.children:
        rendered = answer_view(child)
        if rendered.strip():
            parts.append(rendered)
    return "；".join(parts)


def is_multi_value(module_id: str, subfield_id: str) -> bool:
    """D23：多值字段判定（数据驱动——SubField.multi，story_modules 声明）。"""
    sf = get_subfield(module_id, subfield_id)
    return bool(sf.get("multi")) if sf else False


def _find_child_by_prefix(node: AnswerNode, target: str) -> AnswerNode | None:
    """D23 equivalent merge_target 定位：开头文字前缀匹配（取 12 字）。"""
    t = (target or "").strip()
    if not t:
        return None
    prefix = t[:MERGE_TARGET_PREFIX_CHARS]
    for child in node.children:
        if child.text.strip().startswith(prefix):
            return child
    return None


def _node_contains_exact(node: AnswerNode, value: str) -> bool:
    """Branch 2 节点版同值短路：node 任一层（含递归 children）精确等于 value。"""
    if node.text == value:
        return True
    return any(_node_contains_exact(c, value) for c in node.children)


def proposal_question_text(
    label: str, old: str, new: str, conflict_note: str = ""
) -> str:
    """三选一提案模板问句（单源——两处调用点共用，输出逐字节一致）。"""
    conflict_part = f"（{conflict_note}）" if conflict_note else ""
    return (
        f"你之前定过【{label}】是『{old}』{conflict_part}。"
        f"这次的『{new}』——是要**替换**它，"
        f"还是两者**合并**（同一条里都保留），"
        f"还是先**放弃**这条修改？"
    )


_AUTO_MERGE_LOG_CAP = 20  # 滚动上限：轻量披露不无限膨胀
ANSWER_CHILDREN_CAP = 6  # D23 拍板 4——多值字段子条目上限（非清单位点默认）
MERGE_TARGET_PREFIX_CHARS = 12  # merge_target 前缀定位长度


def _children_cap(subfield_id: str) -> int:
    """清单帽位点表驱动（批B）：LIST_CAPS 命中按表取值（6/12 两档），
    未命中回退 D23 默认 ANSWER_CHILDREN_CAP——12 帽位点
    （existence/key_nodes/material_pool）不再被硬编码 6 提前截断。"""
    return LIST_CAPS.get(subfield_id, ANSWER_CHILDREN_CAP)


# ---------------------------------------------------------------------------
# 批B：三-tier 树消费面（L3 值 schema + 树写/读入口）
#
# 存储布局（answers 平面键集合零新增）：
# - 锚节点键 = L2 id（无点号，永不与 module.field 平面宇宙相交）；
#   值 = AnswerNode(text=L2 label, children=[L3 节点...])。
# - L3 节点 source = l3_id（树定位可回放）；结构化部件存为
#   source=部件键 的子节点（⇉ change 部件嵌套子节点）；
#   清单追加存 source="" 的子节点（D23 complement 同构）。
# ---------------------------------------------------------------------------


def _build_l3_index() -> dict[str, dict[str, Any]]:
    """THREE_TIER_TREE → l3_id 定位表（惰性一次性构建，纯数据投影）。"""
    idx: dict[str, dict[str, Any]] = {}
    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:
            for l3 in l2["l3"]:
                idx[str(l3["id"])] = {
                    "l1_id": l1["id"],
                    "l1_label": str(l1.get("label", "")),
                    "l2_id": str(l2["id"]),
                    "l2_label": str(l2.get("label", "")),
                    "vs": str(l3["vs"]),
                }
    return idx


_L3_INDEX = _build_l3_index()

#: vs → 合法部件键闭集（⑥稿 §0 判定表；半填 = 键可缺，不允许越集）。
_L3_PART_KEYS: dict[str, frozenset[str]] = {
    VS_FROM_TO: frozenset({"from", "to", "trigger"}),
    VS_DIM_DIR: frozenset({"dimension", "direction", "magnitude"}),
    VS_DUAL: frozenset({"point", "change"}),
}

#: 数值部件键（落库为文本、读回转数值；magnitude=0 是真实内容不是空）。
_L3_NUMERIC_PART_KEYS = frozenset({"magnitude"})


def validate_l3_value(l3_id: str, value: Any) -> bool:
    """值 schema 校验入口（批B）。合法 → True；形状越界 → ValueError。

    - ● 位点只认纯文本：结构化 dict → 拒绝（拒绝或降级二选一，本实现
      选拒绝——调用方可用 _l3_render 自行降级）。
    - ▶/⇄/⇉ 位点：dict 半填缺字段宽容；str 降级为点形态文本。
    - 幅度 0 合法（⑥§2-16 拒绝线特例：数值部件不查真值）。
    - 树外位点（旧 35 字段宇宙）→ 惯例按 ● 处理，恒合法。
    """
    meta = _L3_INDEX.get(l3_id)
    if meta is None:
        return True
    vs = meta["vs"]
    if vs == VS_POINT:
        if isinstance(value, dict):
            raise ValueError(f"● 位点不接受结构化值：{l3_id}")
        return True
    if isinstance(value, str):
        return True
    if not isinstance(value, dict):
        raise ValueError(f"不支持的值形态：{l3_id}（vs={vs}）")
    allowed = _L3_PART_KEYS.get(vs, frozenset())
    for k in value:
        if allowed and k not in allowed:
            raise ValueError(f"未知值字段 {k!r}（位点 {l3_id}，vs={vs}）")
    return True


def _l3_render(value: Any) -> str:
    """结构化值 → 渲染串（叶值深度优先「；」连接；answer_view dict 支路复用）。"""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        leaves: list[str] = []

        def _walk(v: Any) -> None:
            if isinstance(v, dict):
                for x in v.values():
                    _walk(x)
            else:
                leaves.append(str(v))

        _walk(value)
        return "；".join(leaves)
    return str(value)


def _l3_part_node(part_key: str, part_value: Any) -> AnswerNode:
    """部件键/值 → 部件节点（⇉ change 等嵌套 dict → 嵌套部件子节点）。"""
    if isinstance(part_value, dict):
        return AnswerNode(
            source=part_key,
            children=[_l3_part_node(k, v) for k, v in part_value.items()],
        )
    return AnswerNode(source=part_key, text=str(part_value))


def _l3_part_scalar(node: AnswerNode) -> Any:
    """部件节点 → 标量值（数值部件键转数值——magnitude=0 落库可查）。"""
    if node.source in _L3_NUMERIC_PART_KEYS:
        try:
            return int(node.text)
        except ValueError:
            try:
                return float(node.text)
            except ValueError:
                pass
    return node.text


def _l3_parse_node(node: AnswerNode) -> dict[str, Any]:
    """L3 节点 → 结构化部件 dict；无部件（●/降级点形态）→ {"point": 渲染串}。"""
    parts: dict[str, Any] = {}
    for c in node.children:
        if c.source:
            if c.children:
                parts[c.source] = {
                    gc.source: _l3_part_scalar(gc) for gc in c.children if gc.source
                }
            else:
                parts[c.source] = _l3_part_scalar(c)
    if parts:
        return parts
    return {"point": answer_view(node)}


def l3_value_node(value: Any) -> AnswerNode | str:
    """结构化部件 dict → 扁平 AnswerNode（批E-1 上传联动消费面）。

    部件存 source=部件键 子节点 + 渲染串入 text（与 apply_l3_fill 落库
    形态同构），l3_value_parts 可读回部件。非 dict → 原样返回（● 纯文本）。
    """
    if not isinstance(value, dict):
        return value if isinstance(value, str) else str(value)
    return AnswerNode(
        text=_l3_render(value),
        children=[_l3_part_node(k, v) for k, v in value.items()],
    )


def _l3_lookup(session_or_answers: Any, l3_id: str) -> Any:
    """L3 定位读：平面遗留键（l2.l3 旧宇宙成员）优先，其次 L2 锚树内扫描。"""
    answers = getattr(session_or_answers, "answers", session_or_answers)
    meta = _L3_INDEX.get(l3_id)
    if meta is None:
        return answers.get(l3_id, "")
    flat_key = f"{meta['l2_id']}.{l3_id}"
    if flat_key in answers:
        return answers[flat_key]
    anchor = answers.get(meta["l2_id"])
    if isinstance(anchor, AnswerNode):
        for c in anchor.children:
            if c.source == l3_id:
                return c
    return ""


def l3_value_parts(session_or_answers: Any, l3_id: str) -> dict[str, Any]:
    """结构化值读入口（批B）：l3_id → 部件 dict。

    - ●/降级点形态 → {"point": 文本}；▶/⇄/⇉ → 部件键 dict（⇉ change 嵌套）。
    - 无 vs 标注的存量平面串答案 → 全按 ● 处理（{"point": 原串}）。
    - 未写入 → {}。
    """
    found = _l3_lookup(session_or_answers, l3_id)
    if isinstance(found, AnswerNode):
        return _l3_parse_node(found)
    if isinstance(found, str) and found:
        return {"point": found}
    return {}


def _l3_truthy_leaf(value: Any) -> bool:
    """真值闸树扩展（复用 J1 is_truthy_answer 语义，不发明第二套判定）：
    字符串走 is_truthy_answer；数值即真实内容（magnitude=0 不是空）；
    dict/AnswerNode 递归——任一部件真实即真值（半填宽容）。"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return is_truthy_answer(value)
    if isinstance(value, AnswerNode):
        return _l3_truthy_leaf(_l3_parse_node(value))
    if isinstance(value, dict):
        return any(_l3_truthy_leaf(v) for v in value.values())
    return False


def l3_answer_truthy(value_or_answers: Any, key: str | None = None) -> bool:
    """树真值谓词（批B）：有真实内容即真值——半填与全填同判。

    两种调用形：l3_answer_truthy(值)（直接判值）/
    l3_answer_truthy(answers|session, l3_id)（按位点定位后判值）。
    """
    if key is None:
        return _l3_truthy_leaf(value_or_answers)
    found = _l3_lookup(value_or_answers, key)
    if isinstance(found, str) and not found:
        return False
    return _l3_truthy_leaf(found)


def read_l3_answer(session: Any, l3_id: str) -> AnswerNode:
    """L3 树读入口（批B）：l3_id → AnswerNode（未写入 → 空 node）。"""
    found = _l3_lookup(session, l3_id)
    return found if isinstance(found, AnswerNode) else AnswerNode()


def _l3_node_contains(node: AnswerNode, rendered: str) -> bool:
    """L3 同值短路：节点 text 或任一追加条目精确等于 rendered。"""
    if node.text == rendered:
        return True
    return any(c.text == rendered for c in node.children if not c.source)


def _l3_assign(session: Any, l3_id: str, value: Any, rendered: str) -> None:
    """首次写入/覆写：结构化 dict → 部件子节点 + 渲染串入 text；str → text。"""
    node = read_l3_answer(session, l3_id)
    if isinstance(value, dict):
        kept = [c for c in node.children if not c.source]
        node.children = kept + [
            _l3_part_node(k, v) for k, v in value.items()
        ]
    node.text = rendered


def _l3_merge_parts(node: AnswerNode, value: dict[str, Any], rendered: str) -> None:
    """结构化补充/归并：按部件键并入（已有部件覆写、缺字段宽容保留）。"""
    remaining = [c for c in node.children if not c.source]
    new_parts = [_l3_part_node(k, v) for k, v in value.items()]
    node.children = remaining + new_parts
    if not node.text.strip():
        node.text = rendered


def apply_l3_fill(
    session: Any,
    l3_id: str,
    value: Any,
    relation: str | None = None,
    merge_target: str | None = None,
    merged_value: str | None = None,
    conflict_note: str = "",
) -> dict[str, Any]:
    """L3 树写入口（批B）：57 新 L3 答案以 AnswerNode children 挂 L2 锚下。

    - 57 新 L3 不进 A1Session 平面字段（锚键 = L2 id，无点号）；
      D23 语义归并（等价/补充/矛盾）在 L3 层沿用。
    - relation 缺省 = 直写（同值短路）；complement = 追加条目/并入部件；
      equivalent = 同值短路 + 归并（点形态拼串同构）；conflict = 三选一
      提议流（pending_proposals，resolve_proposal 拍板）。
    - 半填宽容：结构化 dict 缺字段不拒绝，落库部分形状。
    """
    meta = _L3_INDEX.get(l3_id)
    if meta is None:
        raise ValueError(f"树内无此 L3：{l3_id}")
    validate_l3_value(l3_id, value)
    answers = session.answers
    l2_id = meta["l2_id"]
    rel = (relation or "").strip().lower()
    rendered = _l3_render(value)

    anchor = answers.get(l2_id)
    if not isinstance(anchor, AnswerNode):
        legacy = anchor if isinstance(anchor, str) else meta["l2_label"]
        anchor = AnswerNode(text=legacy)
        answers[l2_id] = anchor
    node = next((c for c in anchor.children if c.source == l3_id), None)
    if node is None:
        node = AnswerNode(source=l3_id)
        anchor.children.append(node)

    if rel == "complement":
        if isinstance(value, dict):
            _l3_merge_parts(node, value, rendered)
        else:
            node.children.append(AnswerNode(text=rendered))
            if not node.text.strip():
                node.text = rendered
        return {"applied": True, "l3_id": l3_id, "anchor": l2_id}

    if rel == "equivalent":
        if _l3_node_contains(node, rendered):
            return {"applied": False, "l3_id": l3_id, "reason": "duplicate"}
        if isinstance(value, dict):
            _l3_merge_parts(node, value, rendered)
        elif merge_target and (fill_child := _find_child_by_prefix(node, merge_target)):
            fill_child.text = (merged_value or "").strip() or rendered
        elif node.text.strip():
            node.text = f"{node.text}；{rendered}"
        else:
            node.text = rendered
        return {"applied": True, "l3_id": l3_id, "anchor": l2_id}

    if rel in ("", "none", "unknown", "point", "direct"):
        if node.text == rendered:
            return {"applied": False, "l3_id": l3_id, "reason": "duplicate"}
        _l3_assign(session, l3_id, value, rendered)
        return {"applied": True, "l3_id": l3_id, "anchor": l2_id}

    # conflict / 其余语义 → D23 三选一提议流（等价归并达帽同路，见
    # _apply_fills 清单停驻出口③）。
    proposal = Proposal(
        module=l2_id,
        subfield=l3_id,
        old=answer_view(node),
        new=rendered,
        conflict_note=conflict_note,
        question_text="",
    )
    pk = _proposal_key(l2_id, l3_id, rendered)
    session.pending_proposals[pk] = {
        "proposal": proposal,
        "options": ["replace", "merge", "drop"],
    }
    return {"applied": False, "l3_id": l3_id, "proposal_key": pk}


def _record_auto_merge(
    session: A1Session,
    key: str,
    sf: dict[str, Any] | None,
    prev: Any,
    new: str,
    merged: str,
    direct_key: str,
    kind: str = "equivalent",
) -> str:
    """D23 记录一次自动合并（轻量披露 + 可撤销），返回 undo token。

    prev 必须是调用方传入的深拷贝快照（model_copy(deep=True) 或 str 原值
    ——str 不可变天然快照）；此处不做拷贝。
    """
    token = uuid.uuid4().hex[:12]
    label = sf["label"] if sf else key.split(".")[-1]
    session.auto_merge_log.append({
        "token": token,
        "field_key": key,
        "label": label,
        "old": answer_view(prev),
        "new": new,
        "merged": merged,
        "kind": kind,
    })
    if len(session.auto_merge_log) > _AUTO_MERGE_LOG_CAP:
        session.auto_merge_log = session.auto_merge_log[-_AUTO_MERGE_LOG_CAP:]
    session.merge_undo[token] = {"key": key, "prev": prev}
    mark_field_source(
        session, key,
        FIELD_SOURCE_HUMAN if key == direct_key else FIELD_SOURCE_LLM_FILL,
    )
    return token


def undo_auto_merge(session: A1Session, token: str) -> dict[str, Any]:
    """D23 撤销一次自动合并（幂等：未知/已撤销 token → restored=False）。"""
    snap = session.merge_undo.pop(token, None)
    if snap is None:
        return {"restored": False, "error": "not_found"}
    session.answers[snap["key"]] = snap["prev"]
    # 乱序撤销——旧快照恢复后，同键后续合并的快照与披露全部作废
    stale_tokens = {
        r["token"] for r in session.auto_merge_log
        if r.get("field_key") == snap["key"] and r["token"] != token
    }
    session.auto_merge_log = [
        r for r in session.auto_merge_log if r["token"] not in stale_tokens
    ]
    for t in stale_tokens:
        session.merge_undo.pop(t, None)
    session.auto_merge_log = [
        r for r in session.auto_merge_log if r["token"] != token
    ]
    return {"restored": True, "field_key": snap["key"]}


class A1Session(BaseModel):
    """A1 guided-session state (10 modules x subfields, sequential)."""

    session_id: str
    user_id: str
    ip_code: str = ""
    current_module: str = Field(default_factory=lambda: first_module()["id"])
    current_subfield: str = Field(default_factory=_initial_subfield)
    # D23：答案值支持 str | AnswerNode（层级条目；存量 str 零迁移 G3——
    # 读取面统一经 answer_view 渲染，落库/门禁行为不变）。
    answers: dict[str, str | AnswerNode] = Field(default_factory=dict)
    phase: str = PHASE_ASKING
    # Seed context (chosen preset or custom idea) — injected into the
    # interviewer prompt so the LLM guides consistently with the seed.
    seed_name: str = ""
    seed_genre: str = ""
    seed_description: str = ""
    # E1-Lite 冲动类型档案（仿 seed_* 三字段模式，spec §11.1-①）。
    # 空串 = 无 profile（存量会话/未走冲动卡路径）→ 队列与锚点全部走默认。
    creator_primary: str = ""
    creator_secondary: str = ""
    creator_profile_source: str = ""  # 仅 "impulse_cards"
    # M1 模块注册表：会话落定的配方（start_session 按 creator_primary 查
    # RECIPES 落定）。recipe_id="default" / recipe_modules=[]（空=default
    # 全集）→ 存量会话零迁移（G3，creator_* 先例），行为逐字节不变。
    recipe_id: str = "default"
    recipe_modules: list[str] = Field(default_factory=list)
    # Anti-stall tracking (deterministic fallback after repeated stalls)
    stall_subfield: str = ""
    stall_count: int = 0
    # Seed-referenced examples offered by the anti-stall guard; the user
    # may reply with a bare number 1/2/3 to accept one directly.
    pending_suggestions: list[str] = Field(default_factory=list)
    # D24 ①知识对话态（2026-10-10 施工单 §1.3）：active=用户在聊领域知识
    # 话题（fills 冻结防误填）；turns=知识态内轮数（>3 强制复位防卡死）。
    # 判定集中单点 _update_knowledge_thread；additive 默认值=存量会话零迁移。
    knowledge_thread_active: bool = False
    knowledge_thread_turns: int = 0
    # Write-guard proposals (Task 4): key=proposal_key, value=dict with
    # 'proposal' (Proposal model), 'options' (list[str]).
    # Semantically independent from pending_suggestions (Metis Q5).
    pending_proposals: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Merge count per field key (module.subfield). After 3 merges,
    # the 'merge' option is removed from future proposals.
    merge_counts: dict[str, int] = Field(default_factory=dict)
    # J4 预算护栏披露：answer value 超 2000 字被截断的记录（finalize 时
    # 并入 warning ledger，source=answers）。
    answer_clips: list[str] = Field(default_factory=list)
    # Fields whose current value came from upload prefill (LLM *guesses*,
    # never user-confirmed). User-spoken fills overwrite these directly
    # (write guard protects user-confirmed content only); the key is
    # removed after overwrite so the field returns to normal guard.
    prefill_fields: list[str] = Field(default_factory=list)
    # M4a（D12）：answers 的平行溯源元数据，同键空间 dict[str, str]。
    # 四来源闭集见 FIELD_SOURCES；default {} 零迁移（G3 先例——存量会话
    # model_validate 直接通过，读侧 .get(key, "unknown") 兜底）。只看不判。
    field_sources: dict[str, str] = Field(default_factory=dict)
    # M4a 推断包（DN5 新 LLM 生产方）confirm 判定双写：creator_profile
    # 置信棘轮（bucket=creator_primary，[0,1]，确定性增量，全留痕见
    # inference_pack.apply_pack_feedback）。default {} 零迁移。
    creator_confidence: dict[str, float] = Field(default_factory=dict)
    # M0 止血（甲计划任务 0）：叙事素材归档槽（spec L251 character_sketch
    # 文本槽先行版）。默认 "" 零迁移（creator_* 先例）。不进 35 字段/门禁/
    # graphify——素材追加写入（\n 分隔，clip_answer 2000 限额+J3 披露）。
    character_sketch: str = ""
    # M0 止血：同字段连续偏转计数（key=module.subfield）。
    deflect_counts: dict[str, int] = Field(default_factory=dict)
    # M0 止血：连续偏转 ≥2 的字段归档（结构化记录，OpenQuestion.dump 格式，
    # 状态=skipped——参考 C6 open_questions 机制；会话级先行，file 层接线归后续）。
    open_question_archive: list[dict[str, Any]] = Field(default_factory=list)
    # M4b 冲动坐标三件套（impulse spec §10.1）：dict 形态（axis/confidence/
    # safety_flag/audit/...），default {} 零迁移。**E2 只看不判**——本文件
    # 的路由/门禁/队列逻辑零消费，只有 impulse_coords.apply_signal 写入。
    impulse_coords: dict[str, Any] = Field(default_factory=dict)
    # M4b 看门狗轮次计数（handle_message 每次调用 +1；default 0 零迁移）。
    message_rounds: int = 0
    # D20 动态模块调用（2026-09-25 产品方裁决）：用户提及世界观设定内容 →
    # 动态加入会话的世界建构模块 id（LLM 提议 + 确定性校验，LLM 绝不直写）。
    # default [] 零迁移（G3）。invited 是机会性增益：不进定稿门禁（零强制），
    # 每会话 ≤4，插入点 = 当前模块之后（语境相邻）。
    invited_modules: list[str] = Field(default_factory=list)
    # D21 收尾三连问状态机（closing_flow.py，spec v1.3 §5.4）。
    # closing_step: 0=未触发; 1..3=当前待答问题序号; settled 后归零。
    # closing_settled: 三问全部落定（永不重触发）。closing_answers:
    # q1/q2/q3 → 语义答案（generate_doc/continue/ai_fill_yes/...）。
    # resume_later: 「改天继续」同会话持久化标记（D21⑨，不建新会话）。
    # default 零迁移（G3 先例——存量会话 model_validate 直通）。
    closing_step: int = 0
    closing_settled: bool = False
    closing_answers: dict[str, str] = Field(default_factory=dict)
    resume_later: bool = False
    # T16 对齐四动作提案池（alignment_flow.py，D21⑬）：additive 独立容器
    # （照 pending_proposals 惯例但键独立，勿混用；default {} 零迁移 G3）。
    # LLM 只提议（确定性校验器单点过滤）；应用 = 确定性代码，LLM 绝不直写。
    pending_alignments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # T15（D15③/D21⑬）：会话态草稿版本递进（α 体系）状态槽。结构见
    # a1.draft_version.new_draft_state()——纯内存 dict（baseline/round/
    # step），default 零迁移（G3 先例）。**硬红线：α 绝不进持久层**，
    # graph_code_issuer 整型 vN 发号机制零改动。
    draft_alpha: dict[str, int] = Field(
        default_factory=lambda: draft_version.new_draft_state()
    )
    # D23 自动合并轻量披露账本（等价合并不确认、可撤销——须披露可观测）。
    # default [] 零迁移（G3 先例）。
    auto_merge_log: list[dict[str, Any]] = Field(default_factory=list)
    # D23 自动合并撤销快照：token → {"key","prev"(深拷贝)}。default {} 零迁移。
    merge_undo: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # 方向A一期：当前问的默认选项（D-3 新字段——pending_suggestions 随
    # stall==2 分支退役为死字段：不删不写，零迁移）。空 = 本轮无选项。
    current_options: list[str] = Field(default_factory=list)
    # P3 止血（wave1 T3）：current_options 的归属题键绑定戳（
    # f"{module}.{subfield}"，= options 生成语境所在题）。空串 = 未绑定
    # （直设/旧版存量数据——直选通道放行以保 D-4 兼容）。绑定后直选仅在
    # options_key == 当前题键时消费，杜绝跨题错配（default "" 零迁移，
    # G3 先例）。
    options_key: str = ""
    # D-2：连续 reroll 计数（上限 2；任一非 reroll 输入清零）。
    reroll_streak: int = 0
    # 波次二拍2-13：灵感架（material_pool）——投递素材暂存区，永不拒绝；
    # 条目 = {原文, 建议槽位, ...}（⑤稿 §9.3 灵感架位点，上限 LIST_CAPS
    # ["material_pool"]=12）。default [] 零迁移（G3 先例）。
    material_pool: list[dict[str, Any]] = Field(default_factory=list)
    # 波次二拍2-13/2-16：清单追加循环停驻状态（⑤稿 §9.2-3，D24 状态机
    # 先例）——key=当前停驻的清单位点（L3 id / "branch_card"），空串=未
    # 停驻；turns=停驻循环内轮数（达 LIST_CAPS 上限或用户收束即退出）。
    # default ""/0 零迁移（options_key 先例）。
    list_thread_key: str = ""
    list_thread_turns: int = 0
    # 波次二拍2-18（批C，裁定 D26）：讨论镜像通道停驻状态——与
    # knowledge_thread_*（D24）/list_thread_*（批B）声明式样同构紧邻落位。
    # active=用户在虚构内讨论态（镜子式回应轮）；turns=讨论态内轮数
    # （2 轮帽：第 3 轮虚构内追问 → 确定性桥回当前题并复位）。
    # bool=False/int=0 零迁移（G3 先例）。
    mirror_thread_active: bool = False
    mirror_thread_turns: int = 0


def first_question() -> dict[str, Any]:
    """Return the question payload for the very first subfield."""
    m = first_module()
    sf = first_subfield(m["id"])
    return {
        "section": m["id"],
        "section_label": m["label"],
        "sub_id": sf["id"],
        "sub_label": sf["label"],
        "question": sf["question"],
        "hint": sf["hint"],
        "example": sf.get("example", ""),
    }


# 方向A一期：默认选项邀请话术（单点复制控制——前端/测试均引用此文本）。
OPTION_INVITE_TEMPLATE = (
    "这里有几个方向，也可以直接说你的：\n{lines}\n"
    "（回复序号可直选，想换个方向就说「换一批」）"
)

# 方向A一期 D-2：reroll 关键词闭集（不做模糊匹配——防止误触发生成调用）。
REROLL_KEYWORDS = {"换一批", "再来一批", "换组"}
# D-2：连续 reroll 上限（第 3 次起不再触发生成，引导直选/自由输入）。
REROLL_CAP = 2
# D-2：超上限话术（契约10 断言「直接选」「自己的话」子串）。
REROLL_CAP_REPLY = "示例换了几轮了，先试试直接选一个，或用自己的话说说。"

# 批C（拍2-18）：讨论镜像 2 轮帽——讨论态内至多 2 轮镜子式回应，第 3 轮
# 虚构内追问触发确定性桥回当前题并复位（D24 knowledge turns>3 防卡死先例）。
MIRROR_THREAD_CAP = 2
# 批C：重锚显式元命令触发词（分类提示词 7.8 同源；此处供引擎侧确定性兜底
# 识别——LLM 已分类时以 reanchor 键为准，此表仅作文档性闭集）。
REANCHOR_TRIGGER_WORDS = {"梳理一下"}


def _question_payload(session: A1Session) -> dict[str, Any] | None:
    """Build the question payload for the current subfield."""
    if session.phase == PHASE_COMPLETED:
        return None
    m = get_module(session.current_module)
    sf = get_subfield(session.current_module, session.current_subfield)
    if m is None or sf is None:
        return None
    return {
        "section": m["id"],
        "section_label": m["label"],
        "sub_id": sf["id"],
        "sub_label": sf["label"],
        "question": sf["question"],
        "hint": sf["hint"],
        "example": sf.get("example", ""),
        # 方向A一期：additive 键——当前问的默认选项（空列表 = 无选项）。
        "options": list(session.current_options),
    }


def _render_option_invite(options: list[str]) -> str:
    """渲染默认选项邀请块（OPTION_INVITE_TEMPLATE 单点格式化）。"""
    return OPTION_INVITE_TEMPLATE.format(
        lines="\n".join(f"{i}. {opt}" for i, opt in enumerate(options, start=1))
    )


def _attach_default_options(
    session: A1Session,
    result: Any,
    out: dict[str, Any],
    *,
    blocked: bool,
    bound_key: str = "",
) -> None:
    """方向A一期：主路径（fills/chat）轮末默认选项接线（原地改 out）。

    白名单（blocked=True 或 completed 阶段）→ 只清 current_options，
    零渲染。白名单外：examples 非空列表 → 写 current_options 并把邀请
    块追加到 reply 末尾；examples 缺失/空/畸形 → 清空 + reply 逐字节
    不动（降级零痕迹）。

    P3 止血（wave1 T3）：examples 是 LLM 在本轮 turn-start 题（bound_key，
    即调用方 cur_key——sync_position 推进**前**的题）语境下生成的，写入
    时同步打归属题键绑定戳 options_key=bound_key；清空路径一律复位为
    空串。直选通道（D-4）凭该戳拒绝跨题消费。
    """
    if blocked or session.phase == PHASE_COMPLETED:
        session.current_options = []
        session.options_key = ""
        return
    examples = getattr(result, "examples", None)
    if isinstance(examples, list) and examples:
        session.current_options = list(examples)
        session.options_key = bound_key
        out["reply"] += "\n" + _render_option_invite(session.current_options)
    else:
        session.current_options = []
        session.options_key = ""


def sync_position(session: A1Session) -> None:
    """Jump to the first unanswered subfield; complete when none left.

    Gate-aware (user request: 有缺失，在窗口询问): modules still below the
    50% finalize gate are serviced FIRST, so the chat window proactively
    asks about missing modules instead of trailing minor fields elsewhere.

    E1-Lite T2 (spec §5.2 / §12.1.6 R6): the traversal order is
    type-driven via `_type_ordered_modules` (R6 conservative mode:
    forward-only — modules are moved *earlier*, never skipped), so the
    interview opens on the modules that matter for the creator's impulse
    type. Within a module, subfields keep questionnaire-tree order, with
    one exception: when creator_primary hits TYPE_ENTRY_SUBFIELD, the
    entry subfield is swapped to the front of its module (plot/unsure →
    历史时间线.main_plot, so the first question is the story question,
    not time_span).
    """
    ordered = _type_ordered_modules(session)
    entry_mid, entry_sf = _session_entry_subfield(session)

    def _module_subfield_ids(mid: str) -> list[str]:
        sids = [f["id"] for f in subs_for_module(mid)]
        if mid == entry_mid and entry_sf in sids:
            sids.remove(entry_sf)
            sids.insert(0, entry_sf)
        return sids

    # 1) Prefer unfilled fields inside gate-failing modules.
    for mid in ordered:
        if is_module_over_half(mid, session.answers):
            continue
        for sid in _module_subfield_ids(mid):
            key = f"{mid}.{sid}"
            if key not in session.answers:
                session.current_module = mid
                session.current_subfield = sid
                return
    # 2) Fallback: first unanswered across "type-ordered modules × their
    #    original subfield order" (same keys as all_subfield_keys, permuted).
    for mid in ordered:
        for sid in _module_subfield_ids(mid):
            key = f"{mid}.{sid}"
            if key not in session.answers:
                session.current_module = mid
                session.current_subfield = sid
                return
    session.phase = PHASE_COMPLETED


#: D20 闭集：可被动态调用的模块 = 世界建构族（故事/产出模块永不可调用）。
WORLDVIEW_MODULE_IDS: frozenset[str] = frozenset(
    mid for mid, d in MODULE_POOL.items() if d.family == "worldview"
)

#: D20 护栏：每会话动态调用上限（防重复轰炸）。
_INVITE_CAP = 4


def core_recipe_modules(session: A1Session) -> list[str]:
    """定稿门禁视角的核心配方（D20）：recipe_modules - invited_modules。

    invited 模块 = 机会性增益，绝不强制完成（提及魔法一次不得强迫答完
    力量体系 8 问）。存量/默认会话 invited 恒空 → 与原行为逐字节一致。
    """
    walk = session.recipe_modules or module_ids()
    invited = set(session.invited_modules)
    return [mid for mid in walk if mid not in invited]


def _apply_worldview_invites(
    session: A1Session, invites: list[str]
) -> list[str]:
    """D20 单点消费：worldview_invites 的确定性校验与应用。

    LLM 提议（interview JSON 可选键）→ 此处闭集校验后写状态（D-A2-4：
    LLM 永不直写 session 状态）：
    - 闭集 = 世界建构族（WORLDVIEW_MODULE_IDS；故事/产出模块永不可调用）
    - 去重（本轮列表内 + 会话历史）+ 跳过已在游走清单的模块
      （default 全集会话 = 天然 no-op）
    - 每会话上限 4（_INVITE_CAP 护栏）
    - 插入点 = 当前模块之后（语境相邻——在被提及时顺势展开），多个
      按列出顺序依次紧随当前模块插入
    返回实际接受的模块 id（用于披露文案与审计）。
    """
    accepted: list[str] = []
    # 存量/default 会话（recipe_modules 空 = 走查表全集路径）不插入：往空
    # 列表插入会把游走清单收窄为 invited 子集——全集视角天然覆盖，跳过。
    if not invites or not session.recipe_modules:
        return accepted
    walk = session.recipe_modules
    cur_idx = (
        walk.index(session.current_module)
        if session.current_module in walk
        else len(walk) - 1
    )
    for mid in invites:
        if len(session.invited_modules) >= _INVITE_CAP:
            break
        if (
            mid not in WORLDVIEW_MODULE_IDS
            or mid in accepted
            or mid in session.invited_modules
            or mid in walk
        ):
            continue
        cur_idx += 1
        walk.insert(cur_idx, mid)
        session.invited_modules.append(mid)
        accepted.append(mid)
    if accepted:
        log_event(
            session.session_id,
            "worldview_invoked",
            modules=list(accepted),
            trigger="user_mention",
        )
        _reset_stall_tracking(session)
    return accepted


def _invite_notice(accepted: list[str]) -> str:
    """D20 披露文案（确定性模板，初稿措辞）：诚实可观测。"""
    labels = "、".join(
        MODULE_POOL[mid].label if mid in MODULE_POOL else mid
        for mid in accepted
    )
    return (
        f"你提到了{labels}——我把它加入了接下来的引导。"
        "不想聊可以随时说跳过。"
    )


def resolve_proposal(session: A1Session, key: str, choice: str) -> dict[str, Any]:
    """Resolve a pending write-guard proposal.

    Choices: 'replace' | 'merge' | 'drop'.
    Returns dict with 'applied' (bool), 'choice', and optional 'already_resolved'.
    Idempotent: repeating the same key returns latest state without
    double-write (Metis E3).
    """
    entry = session.pending_proposals.get(key)
    if entry is None:
        return {"applied": False, "choice": choice, "error": "not_found"}

    # 批D：灵感架安家提案（rack_home 前缀）——确认=落目标槽 + pool -1 +
    # rack_recycled 事件；拒绝=pool 保留 + 零事件（条目标记 declined，
    # 不再重复提议）。**用户确认铁律**：只有显式 choice 才动 pool。
    if entry.get("rack_home"):
        session.pending_proposals.pop(key, None)
        if choice == "replace":
            target = entry["rack_target"]
            session.answers[target] = entry["rack_text"]
            mark_field_source(session, target, FIELD_SOURCE_LLM_FILL)
            session.material_pool = [
                m for m in session.material_pool
                if m.get("text") != entry["rack_text"]
            ]
            from app.domains.creation.a1 import inspiration_log

            inspiration_log.emit_event("rack_recycled", session, target=target)
            return {"applied": True, "choice": choice}
        # drop / 其余 choice：条目留在架上，标 declined（不再提议）
        for m in session.material_pool:
            if m.get("text") == entry["rack_text"]:
                m["declined"] = True
        return {"applied": False, "choice": choice}

    proposal: Proposal = entry["proposal"]
    field_key = f"{proposal.module}.{proposal.subfield}"

    if choice == "replace":
        session.answers[field_key] = proposal.new
        applied = True
    elif choice == "merge":
        old_val = session.answers.get(field_key, proposal.old)
        if is_multi_value(proposal.module, proposal.subfield):
            # D23：多值字段 merge = 晋升层级条目并追加子条目（不拼串）。
            node = (
                old_val
                if isinstance(old_val, AnswerNode)
                else AnswerNode(text=old_val)
            )
            node.children.append(AnswerNode(text=proposal.new))
            session.answers[field_key] = node
        else:
            session.answers[field_key] = f"{old_val}；{proposal.new}"
        session.merge_counts[field_key] = session.merge_counts.get(field_key, 0) + 1
        applied = True
    elif choice == "drop":
        applied = False
    else:
        return {"applied": False, "choice": choice, "error": "invalid_choice"}

    if applied:
        # M4a 出口 2（fills 通道 confirm 面）：拦截提案经用户 confirm 落写
        # → llm_fill（spec §6：「访谈 fills（已经用户 confirm）」）。
        mark_field_source(session, field_key, FIELD_SOURCE_LLM_FILL)
    # M4b 冲动坐标：显式信号（用户 confirm/drop 动作）→ 确定性更新。
    from app.domains.creation.a1.impulse_coords import (
        SIGNAL_FILL_CONFIRMED,
        SIGNAL_FILL_REJECTED,
        apply_signal,
    )
    apply_signal(
        session,
        SIGNAL_FILL_CONFIRMED if applied else SIGNAL_FILL_REJECTED,
        key=field_key,
    )
    session.pending_proposals.pop(key, None)
    return {"applied": applied, "choice": choice}


def _fallback_divergent(session: A1Session, fills: list[InterviewFill]) -> str | None:
    """Code-level fallback for divergent_question (Metis AC-M8).

    When InterviewResult.divergent_question is None and fills are
    non-empty, generate a template question from fill value keywords
    × unfilled field labels.
    Template: "你提到【{keyword}】，这和＿＿（{unfilled_label}）有关系吗？"
    """
    if not fills:
        return None

    # Determine keys being filled this turn (to exclude them from targets)
    filling_keys = {f"{f.module}.{f.subfield}" for f in fills}

    # Collect unfilled field labels (up to 10, excluding the ones being filled)
    unfilled_labels: list[str] = []
    # M2 G5：发散兜底目标 = 配方并集（None=全集，default 逐字节不变）——
    # 不诱导 LLM/前端把话题引向配方外世界建构字段。
    recipe = session.recipe_modules or None
    for key in all_subfield_keys(recipe):
        if key not in session.answers and key not in filling_keys:
            module_id, sub_id = key.split(".", 1)
            sf = get_subfield(module_id, sub_id)
            if sf:
                unfilled_labels.append(sf["label"])
        if len(unfilled_labels) >= 10:
            break

    if not unfilled_labels:
        return None

    # Use first fill's value (up to 8 chars or first punctuation segment)
    val = fills[0].value
    keyword = val[:8]
    # If there's punctuation within 8 chars, truncate there
    for i, ch in enumerate(val[:8]):
        if ch in ("，", "。", "、", "；", "！", "？", ",", "."):
            keyword = val[:i].strip()
            break

    if not keyword:
        return None

    target = unfilled_labels[0]
    return f"你提到【{keyword}】，这和＿＿（{target}）有关系吗？"


def _proposal_key(module: str, subfield: str, new: str) -> str:
    """Deterministic proposal key: module.subfield:md5[:8]."""
    h = hashlib.md5(new.encode()).hexdigest()[:8]
    return f"{module}.{subfield}:{h}"


def _fill_diff(label: str, module: str, old_v: str, new_v: str) -> dict[str, Any]:
    """D23：自动合并 file_diff 条目（与拦截/直写条目同构）。"""
    return {"field": label, "module": module, "section": label, "old": old_v, "new": new_v}


def _apply_fills(
    session: A1Session, fills: list[InterviewFill]
) -> tuple[list[dict[str, Any]], list[Proposal]]:
    """Persist fills into session.answers with write-guard.

    Three-branch guard (Metis Q1/E2):
      1. Empty field (old=='') → direct write + file_diff(old='').
      2. Non-empty, new == old → skip (no proposal, no write).
      3. Non-empty, new != old → intercept: generate Proposal, do NOT
         write to answers.  The proposal is stored in
         session.pending_proposals.

    Returns (file_diff, intercepted_proposals).
    """
    file_diff: list[dict[str, Any]] = []
    intercepted: list[Proposal] = []
    seen_keys: set[str] = set()
    # M4a 直答判定：fills 命中当前问题字段 = 用户口述直答（human）；
    # 其余字段 = LLM 自动填空（llm_fill）。拦截态不标——confirm 后经
    # resolve_proposal 统一标 llm_fill（spec §6：访谈 fills 已经用户 confirm）。
    direct_key = f"{session.current_module}.{session.current_subfield}"
    # M4b 字段级 ai_fill 粒度（未决①收口）：配方 ai_fill_exclude 声明
    # "留给用户"的字段——LLM fills 在应用点被确定性过滤（直答豁免：
    # 键 == 当前问题字段 = 用户口述，永不过滤）。default/空元组 → 零过滤。
    # 策略按冲动类型解析（recipe_id/recipe_modules 存量两态一致）。
    excluded = set(
        RECIPES[resolve_recipe_id(session.creator_primary)].ai_fill_exclude
    )
    for fill in fills:
        key = f"{fill.module}.{fill.subfield}"
        if key in excluded and key != direct_key:
            log_event(
                session.session_id, "ai_fill_excluded",
                field=key, policy=session.recipe_id,
            )
            continue
        key = f"{fill.module}.{fill.subfield}"
        # J1 答案真值闸（fills 统一出口）：占位值/空串视同"本轮没有提取"——
        # 不写入、不拦截、不占用 first-write-wins 名额（真值 fill 仍可写同 key）。
        if not is_truthy_answer(fill.value):
            continue
        # J4 预算护栏：>2000 字截断（守卫分支与提案一律用截断后的值），
        # 截断事实记入 session.answer_clips（J3 披露）。
        fill_value, was_clipped = clip_answer(fill.value)
        if was_clipped:
            session.answer_clips.append(
                f"答案超{ANSWER_MAX_CHARS}字已截断: {key}（原 {len(fill.value)} 字）"
            )
        if key in seen_keys:  # first write wins this turn
            continue
        seen_keys.add(key)
        sf = get_subfield(fill.module, fill.subfield)
        old = session.answers.get(key, "")
        relation = (getattr(fill, "relation", "") or "").strip().lower()
        # 批B 出口①：直答退出——停驻清单位点收到非 complement 输入
        # （用户直接回答当前问）→ 确定性复位 ""/0（D24 出口①同构）。
        if (
            session.list_thread_key
            and fill.subfield == session.list_thread_key
            and relation != "complement"
        ):
            session.list_thread_key = ""
            session.list_thread_turns = 0

        # Branch 2: skip — same value
        if old and old == fill_value:
            continue

        # Branch 3: intercept — non-empty and different
        if old and old != fill_value:
            # Prefill exemption: prefill values are LLM guesses made at
            # upload time and were never confirmed by the user. A fill
            # spoken by the user directly overwrites them (recorded in
            # file_diff); afterwards the key reverts to normal guarding.
            if key in session.prefill_fields:
                session.prefill_fields.remove(key)
                file_diff.append({
                    "field": sf["label"] if sf else fill.subfield,
                    "module": fill.module,
                    "section": sf["label"] if sf else fill.subfield,
                    "old": old,
                    "new": fill_value,
                })
                session.answers[key] = fill_value
                mark_field_source(
                    session, key,
                    FIELD_SOURCE_HUMAN if key == direct_key else FIELD_SOURCE_LLM_FILL,
                )
                continue
            # ---- D23 语义分流（LLM 判定 relation，引擎确定性消费）----
            # relation 缺失/None/未知 → 落到现行拦截行为（逐字节不变）。
            relation = (getattr(fill, "relation", "") or "").strip().lower()
            # D23 Branch 2 节点版：层级条目任一层已精确含该值 → 同值短路
            # （等价合并不短路——merge_target 可能指向同级条目，需走下方分流）
            if relation != "equivalent" and isinstance(old, AnswerNode) and _node_contains_exact(old, fill_value):
                continue
            label = sf["label"] if sf else fill.subfield

            # 批B 出口③（等价归并达帽）：清单位点帽子只剩一格时，等价归并
            # 不再静默合并 → 改走 D23 提议流（resolve_proposal 拍板）。
            _equivalent_at_cap = (
                relation == "equivalent"
                and fill.subfield in LIST_CAPS
                and isinstance(old, AnswerNode)
                and len(old.children) >= _children_cap(fill.subfield) - 1
            )
            if relation == "equivalent" and not _equivalent_at_cap:
                if isinstance(old, AnswerNode) and (fill.merge_target or "").strip():
                    child = _find_child_by_prefix(old, fill.merge_target)
                    if child is not None:
                        prev_snapshot = old.model_copy(deep=True)
                        merged = (fill.merged_value or "").strip() or fill_value
                        _record_auto_merge(
                            session, key, sf, prev_snapshot, fill_value,
                            merged, direct_key,
                        )
                        child.text = merged
                        file_diff.append(
                            _fill_diff(
                                label, fill.module, answer_view(prev_snapshot), merged
                            )
                        )
                        continue
                    # merge_target miss → fall through to whole-field merge
                prev_snapshot = (
                    old.model_copy(deep=True) if isinstance(old, AnswerNode) else old
                )
                merged = (
                    (fill.merged_value or "").strip()
                    or f"{answer_view(prev_snapshot)}；{fill_value}"
                )
                _record_auto_merge(
                    session, key, sf, prev_snapshot, fill_value, merged, direct_key
                )
                session.answers[key] = merged
                file_diff.append(
                    _fill_diff(label, fill.module, answer_view(prev_snapshot), merged)
                )
                continue
            if relation == "complement" and (
                is_multi_value(fill.module, fill.subfield)
                or fill.subfield in LIST_CAPS
            ):
                cap = _children_cap(fill.subfield)
                if isinstance(old, AnswerNode):
                    node = old
                elif is_multi_value(fill.module, fill.subfield):
                    node = AnswerNode(text=old)  # D23 旧晋升：首条存 text
                else:
                    # 批B 清单位点（非 multi，如 conflict/existence）：
                    # children-inclusive 晋升——全部条目进 children（帽计数
                    # 与 LIST_CAPS 对齐，6 帽第 6 条触发提议、12 帽不提前截断）。
                    node = AnswerNode(text="", children=[AnswerNode(text=old)])
                if len(node.children) < cap - 1:
                    prev_snapshot = (
                        old.model_copy(deep=True)
                        if isinstance(old, AnswerNode)
                        else old
                    )
                    node.children.append(AnswerNode(text=fill_value))
                    _record_auto_merge(
                        session, key, sf, prev_snapshot, fill_value,
                        answer_view(node), direct_key, kind="complement",
                    )
                    session.answers[key] = node
                    # 批B 停驻进入/推进：list 位点补充新条目 → 置位 + turns
                    # 逐轮推进（D24 knowledge_thread 防卡死同构）。
                    if session.list_thread_key == fill.subfield:
                        session.list_thread_turns += 1
                    else:
                        session.list_thread_key = fill.subfield
                        session.list_thread_turns = 1
                    # 批D 埋点收口：清单条目追加事件（fail-silent，additive）。
                    from app.domains.creation.a1 import inspiration_log

                    inspiration_log.emit_event(
                        "list_append",
                        session,
                        module=fill.module,
                        subfield=fill.subfield,
                    )
                    file_diff.append(
                        _fill_diff(
                            label, fill.module,
                            answer_view(prev_snapshot), answer_view(node),
                        )
                    )
                    continue
                # children >= cap-1 → 帽满：falls through to proposal
                # （批B 出口③：帽满话术 + D23 提议流归并 + 复位，见下方落点）
            # conflict / complement-scalar / missing / unknown → 现行三选一拦截
            # 批B 出口③：帽满退出——停驻态确定性复位（复位落点与 D23 提议流
            # 同点：帽满话术由 proposal 问句承载，归并走 resolve_proposal）。
            if session.list_thread_key == fill.subfield:
                session.list_thread_key = ""
                session.list_thread_turns = 0
            proposal = Proposal(
                module=fill.module,
                subfield=fill.subfield,
                old=answer_view(old),
                new=fill_value,
                conflict_note=fill.conflict_note,
                question_text=(getattr(fill, "conflict_question", "") or ""),
            )
            intercepted.append(proposal)
            pk = _proposal_key(fill.module, fill.subfield, fill_value)
            # Determine available options (merge cap check)
            merge_count = session.merge_counts.get(key, 0)
            options = ["replace", "drop"]
            if merge_count < 3:
                options.insert(1, "merge")  # replace, merge, drop
            session.pending_proposals[pk] = {
                "proposal": proposal,
                "options": options,
            }
            continue

        # Branch 1: empty → direct write
        file_diff.append({
            "field": sf["label"] if sf else fill.subfield,
            "module": fill.module,
            "section": sf["label"] if sf else fill.subfield,
            "old": old,
            "new": fill_value,
        })
        session.answers[key] = fill_value
        # 批B 停驻进入：complement 命中清单位点（含首轮直写 old=''）→
        # 置位 + turns=1；后续停驻轮在 complement 追加支路逐轮推进。
        if relation == "complement" and fill.subfield in LIST_CAPS:
            if session.list_thread_key == fill.subfield:
                session.list_thread_turns += 1
            else:
                session.list_thread_key = fill.subfield
                session.list_thread_turns = 1
            # 批D 埋点收口：清单条目首条直写追加事件（与上方补条支路同名）。
            from app.domains.creation.a1 import inspiration_log

            inspiration_log.emit_event(
                "list_append",
                session,
                module=fill.module,
                subfield=fill.subfield,
            )
        mark_field_source(
            session, key,
            FIELD_SOURCE_HUMAN if key == direct_key else FIELD_SOURCE_LLM_FILL,
        )

    return file_diff, intercepted


def _apply_stall_guard(
    session: A1Session,
    text: str,
    cur_key: str,
    result: dict[str, Any],
    interviewer: Interviewer,
) -> dict[str, Any] | None:
    """Anti-stall guard with LLM-understanding-first fallbacks.

    Stall 2 no longer intercepts (方向A一期：默认选项由主路径
    current_options 承担，道歉+示例分支已退役——stall 计数照常累计，
    2 阶原样回落主路径)。Stall >= 3 -> forced_allocate: the LLM judges
    whether the input belongs to ANY legal field; fills are applied,
    otherwise the user gets options (suggestion numbers / rephrase /
    跳过).

    Nothing is ever recorded without LLM judgment (blind-recording fix,
    2026-08-26): the old deterministic raw-text fill is gone.

    Returns a *replacement* result dict when either fallback triggers,
    otherwise None.
    """
    if session.phase == PHASE_COMPLETED:
        return None

    # 1. current field was filled this turn -> reset everything
    if cur_key in session.answers:
        session.stall_subfield = ""
        session.stall_count = 0
        session.pending_suggestions = []
        return None

    # 2. user asked a question -> don't count stall
    if text.strip().endswith(("？", "?")):
        return None

    # 3. track stall count (capped at 3)
    # telemetry: stall（T5 接线 emission；计数站点锚点）
    if session.stall_subfield == cur_key:
        session.stall_count = min(session.stall_count + 1, 3)
    else:
        session.stall_subfield = cur_key
        session.stall_count = 1

    module_id, sub_id = cur_key.split(".", 1)
    from app.domains.creation.a1 import inspiration_log

    inspiration_log.emit_event(
        "stall",
        session,
        module=module_id,
        subfield=sub_id,
        stall_count=session.stall_count,
    )
    sf = get_subfield(module_id, sub_id)
    label = sf["label"] if sf else sub_id

    # 4. stall >= 3 -> LLM forced allocation (judgment; never raw fill)
    if session.stall_count >= 3:
        try:
            alloc = interviewer.forced_allocate(session, text)
        except Exception:  # noqa: BLE001 — degrade, never crash
            alloc = None
        if alloc is not None and alloc.fills:
            file_diff, intercepted = _apply_fills(session, alloc.fills)
            if intercepted:
                # Write guard intercepted — generate confirmation reply
                prop = intercepted[0]
                sf = get_subfield(prop.module, prop.subfield)
                label = sf["label"] if sf else prop.subfield
                result["reply"] = proposal_question_text(
                    label, prop.old, prop.new, prop.conflict_note or ""
                )
                result["next_question"] = None
                result["file_diff"] = []
                result["proposals"] = [p.model_dump() for p in intercepted]
                result["progress"] = progress(session)
                result["phase"] = session.phase
                return result
            sync_position(session)
            if cur_key in session.answers:
                session.stall_subfield = ""
                session.stall_count = 0
                session.pending_suggestions = []
            result["reply"] = alloc.guidance_reply or "已记录。"
            result["next_question"] = _question_payload(session)
            result["file_diff"] = file_diff
            result["progress"] = progress(session)
            result["phase"] = session.phase
            return result

        # no fills (or forced_allocate unavailable) -> record nothing,
        # offer the user concrete options instead.
        if not session.pending_suggestions:
            try:
                examples = interviewer.suggest_examples(session, module_id, sub_id)
            except Exception:  # noqa: BLE001 — degrade, never crash
                examples = []
            if examples:
                session.pending_suggestions = examples
        if session.pending_suggestions:
            seed_label = session.seed_name or session.seed_description[:12] or "种子"
            lines = "\n".join(
                f"{i}. {ex}"
                for i, ex in enumerate(session.pending_suggestions, start=1)
            )
            fallback_reply = (
                f"我仍无法把这条输入对应到「{label}」或任何字段。"
                f"参考种子「{seed_label}」可以选择：\n{lines}\n"
                "直接回复序号、换种说法再答，或回复「跳过」。"
            )
        else:
            fallback_reply = (
                f"我仍无法把这条输入对应到「{label}」或任何字段。"
                "请换种说法再答一次，或回复「跳过」先进入下一项。"
            )
        result["reply"] = (
            (alloc.guidance_reply if alloc is not None and alloc.guidance_reply else "")
            or fallback_reply
        )
        result["next_question"] = _question_payload(session)
        result["file_diff"] = []
        result["progress"] = progress(session)
        result["phase"] = session.phase
        return result

    return None


def _reset_stall_tracking(session: A1Session) -> None:
    session.stall_subfield = ""
    session.stall_count = 0
    session.pending_suggestions = []


def _handle_deflection(
    session: A1Session, result: Any, cur_key: str
) -> dict[str, Any]:
    """M0 止血：消费 interviewer 偏转标记（翻车场景①根治）。

    偏转 = 用户明确表示不想答当前问题/想先聊别的/专注故事主线。旧行为：
    LLM 口头答应但指针不动 → 重问同一题（R6 不答不走死循环）。新行为：
    写占位答案（J1 真值闸 → 门禁不计数）→ sync_position 指针自然前进；
    连续偏转 ≥2 同一字段 → 结构化归档进 open_question_archive（C6 格式）。
    """
    module_id, sub_id = cur_key.split(".", 1)
    sf = get_subfield(module_id, sub_id)
    count = session.deflect_counts.get(cur_key, 0) + 1
    session.deflect_counts[cur_key] = count
    session.answers.setdefault(cur_key, DEFLECT_PLACEHOLDER)

    archived = False
    if count >= 2:
        qid = f"deflect-{cur_key}"
        if not any(r.get("id") == qid for r in session.open_question_archive):
            session.open_question_archive.append(
                OpenQuestion(
                    id=qid,
                    question=(sf or {}).get("question", sub_id),
                    status="skipped",
                    answer=DEFLECT_PLACEHOLDER,
                    source_hint="interview_deflection",
                ).model_dump()
            )
            archived = True
    log_event(
        session.session_id,
        "deflected",
        field=cur_key,
        consecutive=count,
        archived=archived,
    )
    _reset_stall_tracking(session)
    sync_position(session)
    # M4b 冲动坐标：偏转 = 跳过类显式信号（确定性更新，只看不判）。
    from app.domains.creation.a1.impulse_coords import (
        SIGNAL_SKIPPED,
        apply_signal,
    )
    apply_signal(session, SIGNAL_SKIPPED, key=cur_key)
    return {
        "reply": result.guidance_reply or "好，我们先聊你想聊的。",
        "next_question": _question_payload(session),
        "file_diff": [{
            "field": (sf or {}).get("label", cur_key),
            "module": module_id,
            "section": (sf or {}).get("label", cur_key),
            "old": "",
            "new": answer_view(session.answers[cur_key]),
            "deflected": True,
        }],
        "progress": progress(session),
        "phase": session.phase,
    }


def _archive_story_material(
    session: A1Session, result: Any
) -> dict[str, Any]:
    """M0 止血：叙事素材归档（翻车场景②根治）。

    故事型会话中用户输入的人物/场景/情节片段——LLM 已判定其无世界建构
    字段语义（story_material 非空且 fills 空）→ 追加写入 character_sketch
    文本槽（\\n 分隔，clip_answer 2000 限额+J3 披露）。绝不触发已答字段
    的替换/合并/放弃三连提案。素材不是答案：指针不动。
    """
    material = (result.story_material or "").strip()
    clipped, was_clipped = clip_answer(material)
    if was_clipped:
        session.answer_clips.append(
            f"答案超{ANSWER_MAX_CHARS}字已截断: character_sketch"
            f"（原 {len(material)} 字）"
        )
    # M2 素材槽迁移（plan §231）：配方含 M11 角色 → 素材路由进角色模块
    # 第一个未填字段（\n 追加，指针不动——素材不是答案，M0 语义保留）；
    # default/存量会话 → 仍写 character_sketch 文本槽（M0 测试语义不变）。
    recipe_mids = session.recipe_modules or []
    if "角色" in recipe_mids:
        target_sid = next(
            (
                f["id"]
                for f in subs_for_module("角色")
                if not session.answers.get(f"角色.{f['id']}")
            ),
            None,
        )
    else:
        target_sid = None
    if target_sid is not None:
        key = f"角色.{target_sid}"
        existing = session.answers.get(key, "")
        session.answers[key] = f"{existing}\n{clipped}" if existing else clipped
        log_event(
            session.session_id,
            "material_archived",
            target=key,
            chars=len(clipped),
        )
        _reset_stall_tracking(session)
        return {
            "reply": result.guidance_reply or "这段素材我先替你收着。",
            "next_question": _question_payload(session),
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }
    session.character_sketch = (
        f"{session.character_sketch}\n{clipped}"
        if session.character_sketch
        else clipped
    )
    log_event(
        session.session_id,
        "material_archived",
        target="character_sketch",
        chars=len(clipped),
    )
    _reset_stall_tracking(session)
    return {
        "reply": result.guidance_reply or "这段素材我先替你收着。",
        "next_question": _question_payload(session),
        "file_diff": [],
        "progress": progress(session),
        "phase": session.phase,
    }


def _update_knowledge_thread(
    session: A1Session, result: Any, *, frozen: bool = False
) -> None:
    """D24 ①知识对话态状态机（施工单 §1.3——判定集中单点，禁止散落）。

    置位：本轮 knowledge_used=True（搜索成功+二次生效）→ active=True，
    turns=1（已在态内则 +1）。
    保持/退出（active 时逐轮判定）：
    - knowledge_used=True → 保持（turns 已在置位分支推进）；
    - 冻结轮（``frozen`` 或 fills 非空）→ 保持且 turns += 1（anti-stuck：
      施工单原文 turns 只在知识轮推进，但冻结轮若不推进则退出③永不触发；
      逐轮推进保留 §1.3 防卡死本意——解释性偏离，已报告）；
    - fills 空且 knowledge_used=False → 话题自然离开，退出④；
    - turns > 3 → 强制复位，退出③（防卡死）。

    ``frozen`` 标志：冻结发生在状态机更新之前（§1.3 定序），fills 已被
    丢弃，故由冻结点显式传入，状态机才能区分「冻结保持轮」与「自然离开」。
    """
    was_active = session.knowledge_thread_active
    if getattr(result, "knowledge_used", False):
        session.knowledge_thread_active = True
        session.knowledge_thread_turns = (
            session.knowledge_thread_turns + 1 if was_active else 1
        )
    elif was_active:
        if frozen or result.fills:
            session.knowledge_thread_turns += 1  # 冻结保持轮（anti-stuck）
        else:
            session.knowledge_thread_active = False  # 退出④
            session.knowledge_thread_turns = 0
    if session.knowledge_thread_active and session.knowledge_thread_turns > 3:
        session.knowledge_thread_active = False  # 退出③（防卡死）
        session.knowledge_thread_turns = 0


def _reset_mirror_thread(session: A1Session) -> None:
    """批C（拍2-18）：讨论镜像态复位（帽满桥回/话题离开/打断共用单点）。"""
    session.mirror_thread_active = False
    session.mirror_thread_turns = 0


def _build_reanchor_reply(session: A1Session) -> str:
    """批C（拍2-19）：重锚线头清单——配方已完成模块 + 当前题 + 灵感架存量。

    纯确定性拼装（零 LLM）；四选一分流话术（改某答案/跳去聊某条/
    继续当前题/给灵感架安家）。fills 不落槽——重锚轮 answers 零变化。
    """
    lines: list[str] = ["好，我们把手上的线头摊开看一看。"]
    if session.answers:
        lines.append("【已确定的线头】（想改哪条，直接说「把X改成Y」）")
        for key, value in session.answers.items():
            lines.append(f"· {key}：{answer_view(value)}")
    else:
        lines.append("【已确定的线头】还没有——正好从当前题开始。")
    sf = get_subfield(session.current_module, session.current_subfield)
    cur_label = sf["label"] if sf else session.current_subfield
    lines.append(
        f"【当前题】{session.current_module}·{cur_label}——说「继续」就回到这题。"
    )
    if session.material_pool:
        lines.append("【灵感架上还放着】（挑一条说「去聊它」就展开）")
        for item in session.material_pool:
            item_text = str(item.get("text", "")).strip()
            if item_text:
                lines.append(f"· {item_text}")
    lines.append(
        "接下来四选一：改某条答案 / 跳去聊灵感架上的某条 / 继续当前题 / "
        "给灵感架安家（说个新想法我帮你先收着）。"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批D（波次二拍2-13）：灵感架——入架路径 + 自由流程安家提议 + 确认钩子
# ---------------------------------------------------------------------------

#: 灵感架安家提案键前缀（pending_proposals 键空间；entry["rack_home"]=True）。
RACK_PROPOSAL_PREFIX = "rack_home:"
#: 引擎侧确定性确认/保留短语闭集（用户确认铁律：只有这些显式短语才
#: 消费安家提案，其余输入照常走访谈管线；不依赖 LLM 自律）。
RACK_CONFIRM_WORDS = frozenset({"安进去", "安进去吧", "给它安家"})
RACK_KEEP_WORDS = frozenset({"先留着", "留着", "先留着吧"})


def _rack_slots_clause(slots: list[str]) -> str:
    """建议槽位人话片段（≤2 个，点号转间隔号；空 = 兜底句）。"""
    named = [s.replace(".", "·") for s in slots if isinstance(s, str) and s]
    if not named:
        return "——先记着，回头再给它认个门"
    return "——它可能属于" + "或".join(f"『{s}』" for s in named[:2])


def _stow_delivery(session: A1Session, result: Any, text: str) -> str:
    """投递「无家可归」素材入架（永不拒绝）：pool 追加 + rack_stowed 事件。

    帽满（LIST_CAPS["material_pool"]=12）挤最旧——永不拒收（⑤稿 §9.3）。
    返回 rack_stowed 话术（含「灵感架」）。
    """
    from app.domains.creation.seed.story_modules import LIST_CAPS as _LIST_CAPS

    cap = _LIST_CAPS.get("material_pool", 12)
    entry = {
        "text": text.strip(),
        "suggested_slots": list(getattr(result, "suggested_slots", []) or []),
        "created_at": session.message_rounds,
    }
    while len(session.material_pool) >= cap:
        session.material_pool.pop(0)
    session.material_pool.append(entry)
    from app.domains.creation.a1 import inspiration_log

    inspiration_log.emit_event(
        "rack_stowed",
        session,
        chars=len(entry["text"]),
        slots=entry["suggested_slots"],
    )
    return (
        f"记进你的灵感架了{_rack_slots_clause(entry['suggested_slots'])}。"
        "想现在给它找个家，还是先留着？"
    )


def _maybe_propose_rack_homing(session: A1Session, out: dict[str, Any]) -> None:
    """自由流程回收时机①：正常答题轮后提议安家（LLM 只提议，绝不直写）。

    - 候选 = 第一条未 declined 的架上条目；无候选 / 已有挂起安家提案 → 零动作。
    - 提议挂 pending_proposals（rack_home 前缀，resolve_proposal 拍板），
      回复尾追加安家问句（含目标 L3 槽位 + 原文摘要）。
    """
    if not session.material_pool:
        return
    if any(
        k.startswith(RACK_PROPOSAL_PREFIX) for k in session.pending_proposals
    ):
        return
    item = next(
        (m for m in session.material_pool if not m.get("declined")), None
    )
    if item is None:
        return
    target = (item.get("suggested_slots") or [""])[0]
    if not target:
        return
    mod, _, sub = target.partition(".")
    session.pending_proposals[f"{RACK_PROPOSAL_PREFIX}{target}"] = {
        "proposal": Proposal(module=mod or target, subfield=sub or target,
                             old="", new=item["text"]),
        "options": ["安进去", "先留着"],
        "rack_home": True,
        "rack_target": target,
        "rack_text": item["text"],
    }
    out["reply"] = (
        f"{out.get('reply', '')}\n灵感架上还留着一条「{item['text'][:30]}」"
        f"没安家——要把它安进『{target.replace('.', '·')}』吗？"
        "（安进去 / 先留着）"
    )


def _try_rack_homing_reply(session: A1Session, stripped: str) -> dict[str, Any] | None:
    """安家提案的显式短语消费钩子（先于 interviewer，确定性零 LLM）。

    「安进去」→ resolve replace（落槽 + pool -1 + rack_recycled 事件）；
    「先留着」→ resolve drop（pool 保留 + 零事件）。非提案轮 / 非闭集
    短语 → None（照常走访谈管线）。
    """
    keys = [
        k for k in session.pending_proposals
        if k.startswith(RACK_PROPOSAL_PREFIX)
    ]
    if not keys:
        return None
    key = keys[0]
    if stripped in RACK_CONFIRM_WORDS:
        applied = resolve_proposal(session, key, "replace").get("applied")
        if applied:
            return {
                "reply": "好，已给它安家——灵感架上少一件，世界图里多一笔。",
                "next_question": _question_payload(session),
                "file_diff": [],
                "progress": progress(session),
                "phase": session.phase,
            }
    if stripped in RACK_KEEP_WORDS:
        resolve_proposal(session, key, "drop")
        return {
            "reply": "好，先留在灵感架上——想安家时说「安进去」就行。",
            "next_question": _question_payload(session),
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }
    return None


def handle_message(
    session: A1Session,
    text: str,
    interviewer: Interviewer,
) -> dict[str, Any]:
    """M4b 包装：轮次计数 + 看门狗建议附加（additive 可选键 ``watchdog``）。

    决策逻辑零改动（_handle_message_impl 为原函数体）；看门狗只在结果
    dict 上**新增**可选键，不改 reply/next_question/指针（LLM 不进控制
    流——提示内容是确定性模板）。
    """
    session.message_rounds += 1
    out = _handle_message_impl(session, text, interviewer)
    from app.domains.creation.a1.watchdog import check_watchdog

    wd = check_watchdog(session)
    if wd is not None and isinstance(out, dict):
        out.setdefault("watchdog", wd)
    return out


def _handle_message_impl(
    session: A1Session,
    text: str,
    interviewer: Interviewer,
) -> dict[str, Any]:
    """Process one user message with LLM understanding.

    Returns dict with keys:
      reply / next_question / file_diff / progress / phase /
      classification_proposal (optional, only for genuine innovations)

    Rules:
    - "跳过" stores empty string for the current subfield and advances.
    - interviewer fills (possibly many subfields) are persisted; the
      position jumps to the first unanswered subfield.
    - fills empty + is_innovative -> innovation proposal, nothing
      persisted until confirmed.
    - fills empty + not innovative (chat/off-topic) -> reply only.
    - phase 'completed' no longer blocks chat: the user may keep
      refining answers (fills overwrite) until they finalize.
    """
    # T17 同帧定序锚点：模块边界（深对齐）与 provider（轻量检测守门）。
    pre_module = session.current_module
    provider = getattr(interviewer, "_provider", None)

    if session.phase == PHASE_COMPLETED:
        # Completed tree: keep the conversation open for refinement.
        # Falls through to the interviewer below — same routing rules.
        pass

    # D-2：非 reroll 输入 → 连续 reroll 计数清零（跳过/直选/主路径统一生效）。
    if text.strip() not in REROLL_KEYWORDS:
        session.reroll_streak = 0

    # ---- skip ----
    if text.strip() == "跳过":
        # D24 ①退出②：用户显式回到创作流程 → 知识对话态确定性复位。
        session.knowledge_thread_active = False
        session.knowledge_thread_turns = 0
        # 批C：跳过 = 话题离开 → 讨论镜像态同步复位（拍2-18 出口②）。
        session.mirror_thread_active = False
        session.mirror_thread_turns = 0
        # 批B 出口②：跳过退出——清单停驻态归档复位 ""/0。
        session.list_thread_key = ""
        session.list_thread_turns = 0
        answer_key = f"{session.current_module}.{session.current_subfield}"
        skipped_module = session.current_module
        skipped_sf = get_subfield(session.current_module, session.current_subfield)
        session.answers.setdefault(answer_key, "")
        sync_position(session)
        # M4b 冲动坐标：跳过 = 显式信号（确定性更新，只看不判）。
        from app.domains.creation.a1.impulse_coords import (
            SIGNAL_SKIPPED,
            apply_signal,
        )
        apply_signal(session, SIGNAL_SKIPPED, key=answer_key)
        # D-2：跳过 = 非 reroll 输入 → 连续 reroll 计数清零。
        session.reroll_streak = 0
        # telemetry: skip（T5 接线 emission 锚点；结构零改动）
        from app.domains.creation.a1 import inspiration_log

        inspiration_log.emit_event(
            "skip",
            session,
            module=skipped_module,
            subfield=answer_key.split(".", 1)[1],
        )
        return {
            "reply": "已跳过，进入下一项。",
            "next_question": _question_payload(session),
            "file_diff": [{
                "field": skipped_sf["label"] if skipped_sf else answer_key,
                "module": skipped_module,
                "section": skipped_sf["label"] if skipped_sf else answer_key,
                "old": "",
                "new": "",
            }],
            "progress": progress(session),
            "phase": session.phase,
        }

    cur_key = f"{session.current_module}.{session.current_subfield}"

    # ---- default-option number pick ("1"/"2"/"3")（方向A一期 D-4）----
    # 直选绕过占位真值闸（与旧 pick 同一先例：用户显式确认）。
    # P3 止血（wave1 T3）：options 与当前题严格绑定——绑定戳非空且不等于
    # cur_key（生成题 ≠ 当前题，如 fills 推进后的跨题残留）时序号不消费，
    # 落入 interview 文本路径；空戳 = 直设/旧版存量（放行，D-4 兼容）。
    # telemetry: option_pick（T5 接线 emission 锚点；绑定修复后 digest
    # 记录的必然是当前题 options——语义自此修正）。
    stripped = text.strip()
    # 批C（拍2-18/2-19 通道全序）：直选 > 重锚——「2，顺便梳理一下」这类
    # 直选尾缀元命令，数字部分照常直选消费、尾部元命令忽略（不进重锚）。
    if (
        stripped
        and stripped[0] in {"1", "2", "3"}
        and len(stripped) > 1
        and REANCHOR_TRIGGER_WORDS
        and any(w in stripped[1:] for w in REANCHOR_TRIGGER_WORDS)
    ):
        stripped = stripped[0]
    if (
        session.current_options
        and stripped in {"1", "2", "3"}
        and session.phase != PHASE_COMPLETED
        and session.options_key in ("", cur_key)
    ):
        idx = int(stripped) - 1
        if 0 <= idx < len(session.current_options):
            # D24 ①退出①：直选命中 = 回到创作输入 → 先复位知识态再处理。
            session.knowledge_thread_active = False
            session.knowledge_thread_turns = 0
            # 批C 出口③：直选打断讨论镜像态（拍2-18）。
            session.mirror_thread_active = False
            session.mirror_thread_turns = 0
            value = session.current_options[idx]
            options_digest = "|".join(
                str(o) for o in session.current_options[:3]
            )
            session.answers[cur_key] = value
            session.stall_subfield = ""
            session.stall_count = 0
            session.current_options = []
            session.options_key = ""
            sync_position(session)
            module_id, sub_id = cur_key.split(".", 1)
            picked_sf = get_subfield(module_id, sub_id)
            from app.domains.creation.a1 import inspiration_log

            inspiration_log.emit_event(
                "option_pick",
                session,
                module=module_id,
                subfield=sub_id,
                option_index=idx,
                options_digest=options_digest,
            )
            return {
                "reply": f"已按示例记录：{value}",
                "next_question": _question_payload(session),
                "file_diff": [{
                    "field": picked_sf["label"] if picked_sf else cur_key,
                    "module": module_id,
                    "section": picked_sf["label"] if picked_sf else cur_key,
                    "old": "",
                    "new": value,
                }],
                "progress": progress(session),
                "phase": session.phase,
            }

    # ---- reroll（换一批）方向A一期 D-2：关键词触发重生成 ----
    # D-2 例外说明：reroll 是「合并调用承诺」的唯一例外——每次 reroll 额外
    # +1 次 suggest_examples 调用（连续上限 REROLL_CAP=2）；且 stall 计数
    # 一律不动（stall-neutral）。
    if stripped in REROLL_KEYWORDS and session.current_options:
        if session.reroll_streak >= REROLL_CAP:
            # 超上限：不再调用生成，options 保持原样可直选。
            return {
                "reply": REROLL_CAP_REPLY,
                "next_question": _question_payload(session),
                "file_diff": [],
                "progress": progress(session),
                "phase": session.phase,
            }
        examples = interviewer.suggest_examples(
            session, session.current_module, session.current_subfield
        )
        session.reroll_streak += 1
        if isinstance(examples, list) and examples:
            session.current_options = list(examples)
            # P3 止血（wave1 T3）：reroll 产物 = 当前题新选项 → 同步重打
            # 归属题键绑定戳（否则跨题残留下 reroll 后的新选项会被直选
            # 误拒）。reroll 通道其余语义（streak/cap/stall-neutral）零改动。
            session.options_key = cur_key
            # telemetry: option_reroll（T4 已接 emission 调用；T5 落 JSON-lines 落盘）
            from app.domains.creation.a1 import inspiration_log

            inspiration_log.emit_event(
                "option_reroll",
                session,
                module=session.current_module,
                subfield=session.current_subfield,
                streak=session.reroll_streak,
            )
            return {
                "reply": _render_option_invite(session.current_options),
                "next_question": _question_payload(session),
                "file_diff": [],
                "progress": progress(session),
                "phase": session.phase,
            }
        # 空列表/畸形 = suggest 不可用 → 降级：清空选项，引导自由输入。
        session.current_options = []
        return {
            "reply": "这次没想出更多示例，直接说说你的想法也行。",
            "next_question": _question_payload(session),
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- 批D：灵感架安家提案的显式短语消费（先于 interviewer，零 LLM）----
    rack_out = _try_rack_homing_reply(session, stripped)
    if rack_out is not None:
        return rack_out

    result = interviewer.interview(session, text)
    # ---- D24 ①：知识对话态 fills 冻结（先于一切 fills 消费）----
    # active 时本轮 fills 一律丢弃（引擎执行权，不依赖 LLM 自律）；
    # 状态机更新在其后（冻结判定用 pre-update active 态——施工单 §1.3 序）。
    frozen = False
    if session.knowledge_thread_active and result.fills:
        frozen = True
        _dropped = len(result.fills)
        result = result.model_copy(update={"fills": []})
        log_event(
            session.session_id,
            "knowledge_freeze",
            dropped=_dropped,
            turns=session.knowledge_thread_turns,
        )
    _update_knowledge_thread(session, result, frozen=frozen)

    # ---- 批C（拍2-19）：重锚通道——优先于 6.5 知识/镜像/投递/答当前 ----
    # 显式元命令胜出：打断知识对话态与讨论镜像态（互斥复位），摊开线头
    # 清单；本轮 fills 一律不落槽（重锚轮 answers 零变化）。触发双路：
    # LLM 分类键（reanchor）或确定性触发词命中（「梳理一下」闭集）。
    if getattr(result, "reanchor", False) or text.strip() in (
        REANCHOR_TRIGGER_WORDS
    ):
        session.knowledge_thread_active = False
        session.knowledge_thread_turns = 0
        _reset_mirror_thread(session)
        from app.domains.creation.a1 import inspiration_log

        # 双事件名：``reanchor_triggered``（jsonl 落盘契约，
        # test_reanchor）+ ``reanchor``（通道矩阵捕获名，test_channel_matrix_v2）。
        inspiration_log.emit_event("reanchor_triggered", session)
        inspiration_log.emit_event("reanchor", session)
        return {
            "reply": _build_reanchor_reply(session),
            "next_question": _question_payload(session),
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- 批C（拍2-18）：讨论镜像通道——直选/重锚之下、投递/答当前之上 ----
    # mirror_hit 判定：LLM 镜像旗标且本轮不是 6.5 知识轮（知识态优先——
    # 全序 规则6.5知识 > 镜像）。讨论态不吸收 fills（镜子式回应契约）。
    mirror_hit = bool(getattr(result, "mirror", False)) and not bool(
        getattr(result, "knowledge_used", False)
    )
    if session.mirror_thread_active and not mirror_hit:
        # 出口②：话题离开（含直选外的正常作答轮）→ 讨论态归档复位。
        _reset_mirror_thread(session)
    if mirror_hit:
        from app.domains.creation.a1 import inspiration_log

        # 双事件名：``mirror_triggered``（jsonl 落盘契约）+
        # ``discussion_mirror``（通道矩阵捕获名）——同轮双发。
        inspiration_log.emit_event(
            "mirror_triggered", session, turns=session.mirror_thread_turns + 1
        )
        inspiration_log.emit_event("discussion_mirror", session)
        qp = _question_payload(session)
        cur_question = (qp or {}).get("question", "")
        if session.mirror_thread_turns >= MIRROR_THREAD_CAP:
            # 出口①：2 轮帽满——第 3 轮虚构内追问 → 确定性桥回当前题。
            _reset_mirror_thread(session)
            reply = (
                f"{result.guidance_reply}"
                f"（这段推演很有味道——先把它放着，回到手上的问题：{cur_question}）"
            )
        else:
            session.mirror_thread_active = True
            session.mirror_thread_turns += 1
            reply = (
                f"{result.guidance_reply}（回到当前的问题：{cur_question}）"
            )
        return {
            "reply": reply,
            "next_question": qp,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- 批D（拍2-13）：灵感架入架——投递「无家可归」素材，永不拒绝 ----
    # delivery=true 且 fills 留空 = LLM 判定无槽可落 → 入架（帽满挤最旧），
    # rack_stowed 话术 + 事件；指针不动、answers 零变化。
    if getattr(result, "delivery", False) and not result.fills:
        rack_line = _stow_delivery(session, result, text)
        qp = _question_payload(session)
        cur_question = (qp or {}).get("question", "")
        return {
            "reply": (
                f"{result.guidance_reply}{rack_line}"
                f"（回到当前的问题：{cur_question}）"
            ),
            "next_question": qp,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- M0 止血：偏转 → 占位跳过推进指针 ----
    if getattr(result, "deflect", False) and not result.fills:
        _invited = _apply_worldview_invites(session, result.worldview_invites)
        out_deflect = _handle_deflection(session, result, cur_key)
        if _invited:
            out_deflect["reply"] += _invite_notice(_invited)
        # 方向A一期白名单：deflect 轮不渲染选项。
        session.current_options = []
        session.options_key = ""
        return out_deflect

    # ---- M0 止血：叙事素材 → character_sketch 归档（不触发提案三连） ----
    material = getattr(result, "story_material", None)
    if material and material.strip() and not result.fills:
        _invited = _apply_worldview_invites(session, result.worldview_invites)
        out_material = _archive_story_material(session, result)
        if _invited:
            out_material["reply"] += _invite_notice(_invited)
        # 方向A一期白名单：story_material 轮不渲染选项。
        session.current_options = []
        session.options_key = ""
        return out_material

    # ---- genuine innovation -> confirmation flow ----
    if not result.fills and result.is_innovative:
        _invited = _apply_worldview_invites(session, result.worldview_invites)
        return {
            "reply": (result.guidance_reply or "这段内容超出当前分类体系，请确认是否新增。")
            + (_invite_notice(_invited) if _invited else ""),
            "next_question": None,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
            "classification_proposal": ClassificationProposal(
                suggestions=[
                    Suggestion(
                        field=text.strip()[:50],
                        category=result.innovative_category or "其他",
                    )
                ]
            ).model_dump(),
        }

    # ---- fills (possibly many) -> persist + jump to first unanswered ----
    if result.fills:
        # D23：自动合并披露基准（_apply_fills 前取样，取增量）。
        pre = len(session.auto_merge_log)
        file_diff, intercepted = _apply_fills(session, result.fills)

        # Advance position FIRST (when not intercepted) so next_question
        # reflects the post-fill state — asking the just-answered field
        # again ("问两遍" regression) otherwise.
        if not intercepted:
            sync_position(session)

        # Divergent fallback (Metis AC-M8)
        dq = result.divergent_question
        if dq is None:
            dq = _fallback_divergent(session, result.fills)

        # Build base result
        out_fills: dict[str, Any] = {
            "reply": result.guidance_reply or "已记录。",
            "next_question": _question_payload(session),
            "file_diff": file_diff,
            "progress": progress(session),
            "phase": session.phase,
        }
        if dq is not None:
            out_fills["divergent_question"] = dq

        # Write guard intercepted — override reply, suspend next_question
        if intercepted:
            prop = intercepted[0]
            sf = get_subfield(prop.module, prop.subfield)
            label = sf["label"] if sf else prop.subfield
            # D23：单源模板（与 stall 路径逐字节一致）；LLM 人话问句经
            # proposals dump 的 question_text 键披露（D23 契约）。
            out_fills["reply"] = proposal_question_text(
                label, prop.old, prop.new, prop.conflict_note or ""
            )
            out_fills["next_question"] = None  # iron law
            out_fills["file_diff"] = []
            out_fills["proposals"] = [p.model_dump() for p in intercepted]

        # Let stall guard run (preserves stall tracking even when intercepted)
        guard = _apply_stall_guard(session, text, cur_key, out_fills, interviewer)
        if guard is not None:
            out_fills = guard
        # D20 提议消费（stall guard 之后）：闭集校验+写状态+审计；有接受
        # → 追加披露文案（说人话）。置于 guard 后保证 stall 重置不被覆盖。
        _invited = _apply_worldview_invites(session, result.worldview_invites)
        if _invited:
            out_fills["reply"] += _invite_notice(_invited)
        # D21 收尾三连问（T10）+ T17 对齐触发：轮末同帧定序
        # （先对齐后收尾，ROUND_SIGNAL_ORDER；pending 时收尾延后）。
        out_fills = _round_end_signals(
            session, text, out_fills, provider, pre_module=pre_module
        )
        # D23 自动合并轻量披露（最后附加——前面任何 wholesale 替换都不覆盖）。
        new_merges = session.auto_merge_log[pre:]
        if new_merges and not intercepted:
            out_fills["auto_merges"] = [dict(m) for m in new_merges]
            out_fills["reply"] = (
                out_fills["reply"]
                + " "
                + " ".join(
                f"（已把『{m['new'][:20]}』并入【{m['label']}】——不对就说一声撤销。）"
                for m in new_merges
            )
        ).strip()
        # 方向A一期：白名单外轮末接线——write-guard 挂起 / forced_allocate
        # 轮不渲染（blocked），正常轮 examples 非空才追加（D-3/D-4）。
        _attach_default_options(
            session, result, out_fills,
            blocked=bool(intercepted) or guard is not None,
            bound_key=cur_key,
        )
        # 批D 回收时机①：自由流程正常答题轮后 → 灵感架安家提议（additive）。
        _maybe_propose_rack_homing(session, out_fills)
        return out_fills

    # ---- chat / off-topic: reply only, nothing persisted ----
    # 批B 出口④：话题离开退出——无 fills 的闲聊/知识话题 → 清单停驻态
    # 归档复位 ""/0（知识轮除外——D24 冻结/保持语义优先，不构成离开）。
    if session.list_thread_key and not getattr(result, "knowledge_used", False):
        session.list_thread_key = ""
        session.list_thread_turns = 0
    out_chat = {
        "reply": result.guidance_reply or "请围绕当前问题分享你的设定。",
        "next_question": _question_payload(session),
        "file_diff": [],
        "progress": progress(session),
        "phase": session.phase,
    }
    guard = _apply_stall_guard(session, text, cur_key, out_chat, interviewer)
    out = guard if guard is not None else out_chat
    # D20 提议消费（stall guard 之后）：同上，stall 重置不被 guard 覆盖。
    _invited = _apply_worldview_invites(session, result.worldview_invites)
    if _invited:
        out["reply"] += _invite_notice(_invited)
    # D21 收尾三连问（T10）+ T17 对齐触发：同上（同帧定序）。
    out = _round_end_signals(
        session, text, out, provider, pre_module=pre_module
    )
    # D24 ①披露尾注（§1.5）：知识二段成功轮 → 回复尾追加。仅 knowledge
    # 通道；user_confused 路径（knowledge_used=False）不经过此分支。
    if getattr(result, "knowledge_used", False):
        out["reply"] += "\n（已联网查证）"
    # 方向A一期：白名单外轮末接线（forced_allocate 轮 blocked）。
    _attach_default_options(
        session, result, out, blocked=guard is not None, bound_key=cur_key
    )
    return out


# ---------------------------------------------------------------------------
# T17 对齐触发时机 + 同帧定序（问题说明书 L185 触发双档；先对齐后收尾）
# ---------------------------------------------------------------------------

#: 同帧多信号定序规则（显式常量——代码可读出「先对齐后收尾」）：
#: 对齐提案（pending_alignments 非空）时收尾提示延后至全部 resolve；
#: D20 接缝语义保持（受邀问题不阻塞收尾——延后只由 pending 对齐触发）。
ROUND_SIGNAL_ORDER: tuple[str, str] = ("alignment", "closing")


def alignment_hit_terms(
    user_input: str, graph: dict[str, Any] | None
) -> list[str]:
    """轻量命中检测（纯代码零 LLM）：用户新输入与图谱实体词的确定性交集。

    实体词 = 图谱节点标题（与 T14 ``build_graph_digest`` 同源的节点数据、
    同口径——绝不渲染裸节点 id）。空图 / 空输入 → 空交集（不触发）。
    """
    if not isinstance(graph, dict) or not user_input.strip():
        return []
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return []
    terms: set[str] = set()
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        title = str(node.get("title") or "").strip()
        if len(title) >= 2 and title in user_input:
            terms.add(title)
    return sorted(terms)


def alignment_light_hit(
    user_input: str, graph: dict[str, Any] | None
) -> bool:
    """轻量档命中布尔判定（每轮检测零 LLM，命中才进 LLM 提议）。"""
    return bool(alignment_hit_terms(user_input, graph))


def _alignment_notice(session: A1Session) -> str:
    """提案池的用户可见披露（render_proposal 说人话，键域消毒兜底）。"""
    from app.domains.creation.a1.alignment_flow import render_proposal

    graph = graph_digest.lookup_graph_json(session)
    lines = [
        render_proposal(entry["proposal"], graph)
        for entry in session.pending_alignments.values()
    ]
    return "\n【设定对齐建议（待你确认）】\n" + "\n".join(lines)


def _maybe_propose_alignment(
    session: A1Session, text: str, provider: Any, *, pre_module: str
) -> None:
    """对齐触发双档（同帧信号 1，先于收尾执行）。

    - 轻量档：每轮确定性关键词/实体命中（``alignment_light_hit``，
      零 LLM 检测）→ 命中才调 ``AlignmentProposer.propose``（单次
      chat_json，T16 提议流程）。
    - 深档：模块完成边界（``sync_position`` 跨模块，current_module !=
      pre_module）→ 无条件深对齐提议（消费 T14 图谱摘要）。
    - 守门：无 provider / 已有 pending（不做多轮对齐嵌套）→ 零 LLM。
    """
    if provider is None or session.pending_alignments:
        return
    graph = graph_digest.lookup_graph_json(session)
    deep = session.current_module != pre_module
    hit = alignment_light_hit(text, graph)
    if not (deep or hit):
        return  # 每轮 LLM 调用 = 0（计数断言锚点）
    from app.domains.creation.a1.alignment_flow import (
        AlignmentProposer,
        install_proposals,
    )

    pack = AlignmentProposer(provider).propose(graph, text)
    if pack.proposals:
        install_proposals(session, pack.proposals)


def _round_end_signals(
    session: A1Session,
    text: str,
    out: dict[str, Any],
    provider: Any,
    *,
    pre_module: str,
) -> dict[str, Any]:
    """轮末同帧定序（``ROUND_SIGNAL_ORDER``）：先对齐，后收尾。

    - 信号 1 对齐：``_maybe_propose_alignment``（命中/边界 → 提案装包）。
    - 信号 2 收尾：pending_alignments 非空 → 收尾提示延后至 resolve
      （resolve_proposal 先例：提案保留、新消息照常处理，无死锁）；
      为空 → closing_flow.interject 原样接线（T10 已绿行为逐字节保持）。
    """
    _maybe_propose_alignment(session, text, provider, pre_module=pre_module)
    if session.pending_alignments:
        out["reply"] = out.get("reply", "") + _alignment_notice(session)
        return out
    from app.domains.creation.a1.closing_flow import interject as _closing_hook

    return _closing_hook(session, text, out)


def progress(session: A1Session) -> dict[str, Any]:
    """Return {done, total, sections:[{id,label,done,done_fields,total_fields}]} for the UI.

    M2 配方感知：sections/门禁只渲染会话配方内模块（a1_routes._build_sections
    的 M1 先例——recipe_modules 空 = 全集原序，default 输出逐字节不变）。
    """
    ordered = session.recipe_modules or module_ids()
    sections = []
    done_count = 0
    for mid in ordered:
        m = get_module(mid)
        if m is None:
            continue
        fields = m["fields"]
        done_fields = sum(
            1 for f in fields if f"{mid}.{f['id']}" in session.answers
        )
        module_done = done_fields == len(fields) and len(fields) > 0
        if module_done:
            done_count += 1
        sections.append({
            "id": mid,
            "label": m["label"],
            "done": module_done,
            "done_fields": done_fields,
            "total_fields": len(fields),
            "subs": [
                {
                    "id": f["id"],
                    "label": f["label"],
                    "done": f"{mid}.{f['id']}" in session.answers,
                }
                for f in fields
            ],
        })
    return {
        "done": done_count,
        "total": len(ordered),
        "sections": sections,
        # Finalize gate (D20 门禁零强制)：只在核心配方上判定——invited 模块
        # 是机会性增益，不参与 finalizable；core_recipe_modules 对存量/default
        # 会话退化为原 walk（行为逐字节不变）。
        "finalizable": is_finalizable(
            session.answers, recipe=core_recipe_modules(session)
        ),
    }
