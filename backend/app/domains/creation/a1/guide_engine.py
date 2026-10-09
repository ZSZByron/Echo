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


def answer_view(value: str | AnswerNode) -> str:
    """C11 渲染确定性：str 直通；node = 非空片段按深度优先序「；」连接。

    渲染纯函数（同输入同输出，无状态）；空 text/空 children 片段跳过。
    """
    if isinstance(value, str):
        return value
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
ANSWER_CHILDREN_CAP = 6  # D23 拍板 4——多值字段子条目上限
MERGE_TARGET_PREFIX_CHARS = 12  # merge_target 前缀定位长度


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
    # D-2：连续 reroll 计数（上限 2；任一非 reroll 输入清零）。
    reroll_streak: int = 0


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
) -> None:
    """方向A一期：主路径（fills/chat）轮末默认选项接线（原地改 out）。

    白名单（blocked=True 或 completed 阶段）→ 只清 current_options，
    零渲染。白名单外：examples 非空列表 → 写 current_options 并把邀请
    块追加到 reply 末尾；examples 缺失/空/畸形 → 清空 + reply 逐字节
    不动（降级零痕迹）。
    """
    if blocked or session.phase == PHASE_COMPLETED:
        session.current_options = []
        return
    examples = getattr(result, "examples", None)
    if isinstance(examples, list) and examples:
        session.current_options = list(examples)
        out["reply"] += "\n" + _render_option_invite(session.current_options)
    else:
        session.current_options = []


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

            if relation == "equivalent":
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
            if relation == "complement" and is_multi_value(fill.module, fill.subfield):
                node = old if isinstance(old, AnswerNode) else AnswerNode(text=old)
                if len(node.children) < ANSWER_CHILDREN_CAP:
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
                    file_diff.append(
                        _fill_diff(
                            label, fill.module,
                            answer_view(prev_snapshot), answer_view(node),
                        )
                    )
                    continue
                # children >= cap → falls through to proposal (cap, 拍板 4)
            # conflict / complement-scalar / missing / unknown → 现行三选一拦截
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

    # ---- skip ----
    if text.strip() == "跳过":
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
    # telemetry: option_pick（T5 接线 emission 锚点）
    stripped = text.strip()
    if (
        session.current_options
        and stripped in {"1", "2", "3"}
        and session.phase != PHASE_COMPLETED
    ):
        idx = int(stripped) - 1
        if 0 <= idx < len(session.current_options):
            value = session.current_options[idx]
            session.answers[cur_key] = value
            session.stall_subfield = ""
            session.stall_count = 0
            session.current_options = []
            sync_position(session)
            module_id, sub_id = cur_key.split(".", 1)
            picked_sf = get_subfield(module_id, sub_id)
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

    result = interviewer.interview(session, text)

    # ---- M0 止血：偏转 → 占位跳过推进指针 ----
    if getattr(result, "deflect", False) and not result.fills:
        _invited = _apply_worldview_invites(session, result.worldview_invites)
        out_deflect = _handle_deflection(session, result, cur_key)
        if _invited:
            out_deflect["reply"] += _invite_notice(_invited)
        # 方向A一期白名单：deflect 轮不渲染选项。
        session.current_options = []
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
        )
        return out_fills

    # ---- chat / off-topic: reply only, nothing persisted ----
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
    # 方向A一期：白名单外轮末接线（forced_allocate 轮 blocked）。
    _attach_default_options(
        session, result, out, blocked=guard is not None
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
