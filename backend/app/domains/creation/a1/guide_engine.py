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
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.interviewer import (
    Interviewer,
    InterviewFill,
    Proposal,
)
from app.domains.creation.a1.open_questions import OpenQuestion
from app.domains.creation.shared.module_registry import (
    ANCHOR_BY_TYPE,  # noqa: F401 — E1-Lite 数据已迁入注册表，原位置 re-export 兼容
    RECIPES,
    TYPE_ENTRY_SUBFIELD,  # noqa: F401 — 同上（消费侧改为查 Recipe.entry_subfield）
    TYPE_MODULE_PRIORITY,  # noqa: F401 — 同上
    resolve_recipe_id,
)
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


def mark_field_source(session: "A1Session", key: str, source: str) -> None:
    """Tag one answer key with its write source (auto-mark, 都标自动标).

    Raises ValueError on a source outside the closed enum — a typo must
    fail loud at the write site, not silently pollute the metadata.
    """
    if source not in FIELD_SOURCES:
        raise ValueError(f"unknown field source: {source!r}")
    session.field_sources[key] = source


def apply_dice_recommendation(
    session: "A1Session", key: str, value: str
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


def _initial_subfield() -> str:
    """Return the id of the first subfield of the first module."""
    m = first_module()
    sf = first_subfield(m["id"])
    return sf["id"]


class A1Session(BaseModel):
    """A1 guided-session state (10 modules x subfields, sequential)."""

    session_id: str
    user_id: str
    ip_code: str = ""
    current_module: str = Field(default_factory=lambda: first_module()["id"])
    current_subfield: str = Field(default_factory=_initial_subfield)
    answers: dict[str, str] = Field(default_factory=dict)
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
    }


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
            proposal = Proposal(
                module=fill.module,
                subfield=fill.subfield,
                old=old,
                new=fill_value,
                conflict_note=fill.conflict_note,
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

    Stall 2 -> ask the interviewer for seed-referenced example answers
    (user may reply a bare number to accept one). When suggestions are
    unavailable, ask the user to rephrase or 跳过 — no fill.
    Stall >= 3 -> forced_allocate: the LLM judges whether the input
    belongs to ANY legal field; fills are applied, otherwise the user
    gets options (suggestion numbers / rephrase / 跳过).

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
    if session.stall_subfield == cur_key:
        session.stall_count = min(session.stall_count + 1, 3)
    else:
        session.stall_subfield = cur_key
        session.stall_count = 1

    module_id, sub_id = cur_key.split(".", 1)
    sf = get_subfield(module_id, sub_id)
    label = sf["label"] if sf else sub_id

    # 4. stall 2 -> suggestion mode (rely on LLM understanding first)
    if session.stall_count == 2:
        try:
            examples = interviewer.suggest_examples(session, module_id, sub_id)
        except Exception:  # noqa: BLE001 — degrade, never crash
            examples = []
        if examples:
            session.pending_suggestions = examples
            seed_label = session.seed_name or session.seed_description[:12] or "种子"
            lines = "\n".join(
                f"{i}. {ex}" for i, ex in enumerate(examples, start=1)
            )
            result["reply"] = (
                f"我没能准确理解你的回答。参考种子「{seed_label}」，"
                f"这里有几个示例方向：\n{lines}\n"
                "你可以直接回复序号选一个、改写一个再回复、换种说法再答，或回复「跳过」。"
            )
            result["next_question"] = _question_payload(session)
            result["file_diff"] = []
            return result
        # suggestions unavailable -> no fill; ask the user to rephrase / skip
        result["reply"] = (
            f"我还没能理解这条输入与「{label}」的关系。"
            "你可以换种说法再答一次，或回复「跳过」先进入下一项。"
        )
        result["next_question"] = _question_payload(session)
        result["file_diff"] = []
        result["progress"] = progress(session)
        result["phase"] = session.phase
        return result

    # 5. stall >= 3 -> LLM forced allocation (judgment; never raw fill)
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
                conflict_part = f"（{prop.conflict_note}）" if prop.conflict_note else ""
                result["reply"] = (
                    f"你之前定过【{label}】是『{prop.old}』{conflict_part}。"
                    f"这次的『{prop.new}』——是要**替换**它，"
                    f"还是两者**合并**（同一条里都保留），"
                    f"还是先**放弃**这条修改？"
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
            "new": session.answers[cur_key],
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

    # ---- pending-suggestion number pick ("1"/"2"/"3") ----
    stripped = text.strip()
    if (
        session.pending_suggestions
        and stripped in {"1", "2", "3"}
        and session.phase != PHASE_COMPLETED
    ):
        idx = int(stripped) - 1
        if 0 <= idx < len(session.pending_suggestions):
            value = session.pending_suggestions[idx]
            session.answers[cur_key] = value
            session.stall_subfield = ""
            session.stall_count = 0
            session.pending_suggestions = []
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
        return _handle_deflection(session, result, cur_key)

    # ---- M0 止血：叙事素材 → character_sketch 归档（不触发提案三连） ----
    material = getattr(result, "story_material", None)
    if material and material.strip() and not result.fills:
        return _archive_story_material(session, result)

    # ---- genuine innovation -> confirmation flow ----
    if not result.fills and result.is_innovative:
        return {
            "reply": result.guidance_reply or "这段内容超出当前分类体系，请确认是否新增。",
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
            conflict_part = f"（{prop.conflict_note}）" if prop.conflict_note else ""
            out_fills["reply"] = (
                f"你之前定过【{label}】是『{prop.old}』{conflict_part}。"
                f"这次的『{prop.new}』——是要**替换**它，"
                f"还是两者**合并**（同一条里都保留），"
                f"还是先**放弃**这条修改？"
            )
            out_fills["next_question"] = None  # iron law
            out_fills["file_diff"] = []
            out_fills["proposals"] = [p.model_dump() for p in intercepted]

        # Let stall guard run (preserves stall tracking even when intercepted)
        guard = _apply_stall_guard(session, text, cur_key, out_fills, interviewer)
        if guard is not None:
            return guard

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
    return guard if guard is not None else out_chat


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
        # Finalize gate: every module strictly over 50% subfields answered.
        "finalizable": is_finalizable(session.answers, recipe=ordered),
    }
