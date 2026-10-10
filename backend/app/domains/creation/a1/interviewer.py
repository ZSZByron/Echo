"""A1 LLM interviewer — LLM-guided intake instead of template forms.

Core philosophy (2026-08-24 redesign):
    The LLM *understands* free-form user input and fills the structured
    file itself. The question tree is a PROGRESS FRAMEWORK (and a source
    of inspiration), not a rigid template the user must fill word by
    word. A statement is "innovative" ONLY when the LLM judges it to be
    worldview content that falls outside the 10-module taxonomy — a
    plain world name is NEVER innovative.

Contract:
    interview(session, text) -> InterviewResult
      - fills non-empty  -> write answers (possibly many), advance
      - fills empty + is_innovative -> innovation confirmation flow
      - fills empty + not innovative -> chat/off-topic: reply only,
        nothing persisted, position unchanged
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider
from app.domains.creation.a1 import graph_digest  # T14: 模块引用（测试可 patch）
from app.domains.creation.a1.interaction_log import log_event, truncate
from app.domains.creation.seed.a1_question_tree import (
    all_subfield_keys,
    get_module,
    get_subfield,
    module_ids,
)
from app.domains.creation.shared.module_registry import (
    ANCHOR_BY_TYPE,  # noqa: F401 — E1-Lite 数据已迁入注册表，原位置 re-export 兼容
    RECIPES,
    STORY_PRIMARY_TYPES,  # noqa: F401 — 同上（M0 集合随迁）
)


class InterviewFill(BaseModel):
    """One structured write: put value into module.subfield."""

    module: str
    subfield: str
    value: str
    conflict_note: str | None = None
    # D23 语义分流（LLM 判定，引擎确定性消费）：
    relation: str | None = None   # 枚举逐字锁定："equivalent"|"complement"|"conflict"，不允许添加或修改
    merged_value: str | None = None   # equivalent 必填：融合双方要点后的完整表述
    merge_target: str | None = None   # 多值字段只与其中一条等价时：那条的开头文字
    conflict_question: str | None = None  # conflict 必填：面向用户的人话提问（三选一）


class Proposal(BaseModel):
    """A proposed change to an already-filled field."""

    module: str
    subfield: str
    old: str
    new: str
    conflict_note: str | None = None
    merge_preview: str = ""
    # D23：conflict 时 LLM 生成的人话提问（三选一提案卡片问句）；缺省 "" =
    # 现行模板问句逐字节不变（存量保护）。
    question_text: str = ""

    def __init__(self, **data: Any) -> None:
        if "merge_preview" not in data:
            data["merge_preview"] = f"{data.get('old', '')}；{data.get('new', '')}"
        super().__init__(**data)


class InterviewResult(BaseModel):
    """LLM understanding of one user message."""

    fills: list[InterviewFill] = Field(default_factory=list)
    guidance_reply: str = ""
    is_innovative: bool = False
    innovative_category: str | None = None
    divergent_question: str | None = None
    proposals: list[Proposal] = Field(default_factory=list)
    # C7: 用户本轮回答了待问开放问题 → {"id": "...", "answer": "..."}
    open_question_answered: dict | None = None
    # M0 止血（甲计划任务 0）：偏转标记——用户明确表示不想答当前问题/
    # 想先聊别的/专注故事主线 → true，且不生成 fills。
    # 契约豁免（Momus G10）：新增可选字段 = 向前兼容，旧解析器忽略未知键。
    deflect: bool = False
    # M0 止血：叙事素材归档槽——故事型会话中用户输入的人物/场景/情节片段
    # （无可映射世界建构子字段语义）→ 原文要点提取，不生成 fills/提案。
    story_material: str | None = None
    # D20 动态模块调用（2026-09-25 产品方裁决）——LLM 提议通道：
    # 用户本轮输入提及世界建构设定内容 → 建议调用的模块 id 列表。
    # **仅提议，不写状态**：确定性校验（闭集/去重/上限/插入点）在
    # guide_engine 单消费侧（D-A2-4 铁律）。可选键向前兼容（G6b 先例）。
    worldview_invites: list[str] = Field(default_factory=list)
    # 方向A一期（2026-10-08 施工单拍板 2）：默认选项生成通道——与 fills
    # 同 prompt 同返回（合并单次调用）。空 list = 降级（reply 行为与改造前
    # 逐字节一致，降级模式照抄 suggest_examples L636-651 先例）。
    examples: list[str] = Field(default_factory=list)
    # D24 ①（2026-10-10 施工单 §1.3/§1.5）：知识二段成功桥接旗标——
    # knowledge_request 命中且 search reference 非空、二次生成覆盖 raw
    # 时置 True。guide_engine 状态机据此置位知识对话态 + 追加披露尾注。
    # additive 布尔默认 False = 存量行为零扰动（G6b 先例）。
    knowledge_used: bool = False
    # T10（波次一 1.3）投递意图键（additive，D24 knowledge_request 先例）：
    # 规则 6「接住-归位-回题」命中——用户离题想法归位到【可填字段清单】中
    # 既有槽位（fills 可落非当前题的树上已有字段）。仅作意图信号，引擎侧
    # fills 写入路径零变化；A1Session/store/持久化结构零变更（一期边界：
    # 投递式机制设计 §5 施工序一期，落位仍写现有槽）。
    delivery: bool = False


class Interviewer(Protocol):
    def interview(self, session: Any, text: str) -> InterviewResult: ...

    def forced_allocate(self, session: Any, text: str) -> InterviewResult: ...

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]: ...


# ---------------------------------------------------------------------------
# Fakes (tests)
# ---------------------------------------------------------------------------


class FakeInterviewer:
    """Deterministic interviewer for tests."""

    def __init__(
        self,
        fills: list[InterviewFill] | None = None,
        guidance_reply: str = "已记录。",
        is_innovative: bool = False,
        innovative_category: str | None = None,
        raise_error: bool = False,
        examples: list[str] | None = None,
        forced_allocate_result: InterviewResult | None = None,
        proposals: list[Proposal] | None = None,
        open_question_answered: dict | None = None,
        deflect: bool = False,
        story_material: str | None = None,
        worldview_invites: list[str] | None = None,
    ) -> None:
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.is_innovative = is_innovative
        self.innovative_category = innovative_category
        self.raise_error = raise_error
        self._examples = examples
        self._forced_allocate_result = forced_allocate_result
        self._proposals = proposals or []
        self._open_question_answered = open_question_answered
        self._deflect = deflect
        self._story_material = story_material
        self._worldview_invites = worldview_invites or []
        self._pending_open_question: dict | None = None
        self.calls = 0
        self.suggest_calls = 0
        self.forced_calls = 0
        # D23：提案回复一句话分类的固定判定（测试注入）。
        self.confirm_intent: str = "other"

    def classify_confirm_intent(
        self, old_value: str, new_value: str, user_reply: str  # noqa: ARG002
    ) -> str:
        return self.confirm_intent

    def set_pending_open_question(self, question: dict) -> None:
        """C7: 系统注入的待问开放问题（一次一条）。"""
        self._pending_open_question = question

    def take_open_question_answered(self) -> dict | None:
        """C7: 取走本轮 LLM 识别到的待问回答（取后清空）。"""
        answered = self._open_question_answered
        self._open_question_answered = None
        return answered

    def interview(self, session: Any, text: str) -> InterviewResult:
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("llm unavailable")
        return InterviewResult(
            fills=self.fills,
            guidance_reply=self.guidance_reply,
            is_innovative=self.is_innovative,
            innovative_category=self.innovative_category,
            proposals=list(self._proposals),
            open_question_answered=self._open_question_answered,
            deflect=self._deflect,
            story_material=self._story_material,
            worldview_invites=list(self._worldview_invites),
        )

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]:
        self.suggest_calls += 1
        # 方向A一期 reroll 通道（D-2）：ExamplesFake 子类经 self._inject
        # 注入示例——engine 的独立 suggest_examples 调用必须拿到同一注入。
        inject = getattr(self, "_inject", None)
        if isinstance(inject, list) and inject:
            return list(inject)
        if self._examples is None:
            return ["示例一", "示例二", "示例三"]
        return list(self._examples)

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        self.forced_calls += 1
        if self.raise_error:
            raise RuntimeError("llm unavailable")
        if self._forced_allocate_result is not None:
            return self._forced_allocate_result
        return InterviewResult(
            fills=[],
            guidance_reply="无法判断这条输入的归属：请换种说法再答，或回复「跳过」。",
            is_innovative=False,
        )


# ---------------------------------------------------------------------------
# Real LLM implementation
# ---------------------------------------------------------------------------


# D20 动态模块调用：世界建构模块域描述符（prompt 语义目录，逐模块一行）。
# 数据目录（R2：差异是数据不是代码）；id 闭集由 guide_engine 的
# WORLDVIEW_MODULE_IDS（MODULE_POOL family="worldview"）确定性锁定。
WORLDVIEW_DOMAIN_CATALOG: dict[str, str] = {
    "力量体系": "魔法/力量/超自然能力规则",
    "地理空间": "地理/区域/地图/空间格局",
    "文明与社会": "阵营/势力/社会结构/核心价值",
    "历史时间线": "历史/纪元/大事记/时间跨度",
    "世界本体": "世界的本质/基本法则/真实性规则",
    "视觉设计": "视觉风格/美术基调/建筑材质",
    "IP定位": "IP 定位/受众/商业化方向",
    "玩法设计DNA": "玩法机制/玩家角色/核心行动",
    "骰子设定": "骰子/概率/检定/成功机制",
    "设定边界": "不可动设定/禁忌/边界",
}


def _progress_summary(
    answers: dict[str, str], recipe: list[str] | None = None
) -> str:
    """Compact one-line-per-module progress: module: filled/total.

    G5 泄露修复（M2）：recipe 非空时只渲染配方内模块——否则 LLM 被诱导
    提问配方外字段（世界建构轰炸复发通道）。None = 全集（default 逐字节）。
    """
    lines = []
    for mid in module_ids(recipe):
        m = get_module(mid)
        assert m is not None
        total = len(m["fields"])
        done = sum(1 for f in m["fields"] if f"{mid}.{f['id']}" in answers)
        lines.append(f"{mid}: {done}/{total}")
    return "  ".join(lines)


def _immutable_block(answers: dict[str, str]) -> str:
    """Build the 【不可动清单】 content from answers."""
    raw = answers.get("设定边界.immutable_core", "")
    if raw and raw.strip():
        return raw.strip()
    return "（暂无不可动设定）"


def _field_catalog(recipe: list[str] | None = None) -> str:
    """One line per subfield: 'module.subfield: label — question'.

    G5 泄露修复（M2）：recipe 非空时只渲染配方内字段（可填字段清单=配方
    边界）。None = 全集（default 渲染逐字节不变）。
    """
    lines = []
    for mid in module_ids(recipe):
        m = get_module(mid)
        assert m is not None
        for f in m["fields"]:
            lines.append(f"{mid}.{f['id']}: {f['label']} — {f['question']}")
    return "\n".join(lines)


_MAX_ANSWER_DIGEST = 12


def _answers_digest(answers: dict[str, Any]) -> str:
    from app.domains.creation.a1.guide_engine import answer_view  # 延迟导入防环（a1_routes 先例）
    items = [
        f"{k} = {answer_view(v)[:40]}"
        for k, v in list(answers.items())[:_MAX_ANSWER_DIGEST]
        if v
    ]
    return "\n".join(items) if items else "（暂无）"


class RealLLMInterviewer:
    """LLM-guided interviewer built on provider.chat_json.

    All routing decisions (which fields to fill, whether the content is
    genuinely innovative) are made by the LLM. Enum dictionaries and
    templates are only hints inside the prompt, never hard gates.
    """

    def __init__(self, provider: LLMProvider | None) -> None:
        self._provider = provider
        # C7: 系统注入的待问开放问题（一次一条）+ 本轮 LLM 识别到的回答
        self._pending_open_question: dict | None = None
        self._open_question_answered: dict | None = None

    def set_pending_open_question(self, question: dict) -> None:
        """C7: chat 端点注入最老的一条 pending 开放问题。"""
        self._pending_open_question = question

    def take_open_question_answered(self) -> dict | None:
        """C7: 取走本轮 LLM 识别到的待问回答（取后清空）。"""
        answered = self._open_question_answered
        self._open_question_answered = None
        return answered

    def interview(self, session: Any, text: str) -> InterviewResult:
        module = get_module(session.current_module) or {}
        subfield = get_subfield(session.current_module, session.current_subfield) or {}

        system = self._build_prompt(module, subfield, session)
        try:
            raw = asyncio.run(
                self._provider.chat_json(
                    [
                        {"role": "system", "content": system},
                        {"role": "user", "content": text},
                    ]
                )
            )
        except Exception as e:  # noqa: BLE001 — degrade, never crash the session
            log_event(session.session_id, "error", stage="llm_call", error=str(e)[:300])
            raise RuntimeError(f"LLM interview failed: {e}") from e
        log_event(session.session_id, "llm_raw", response=truncate(raw))

        # ---- user confused -> web search -> second pass ----
        if isinstance(raw, dict) and raw.get("user_confused"):
            query = raw.get("search_query")
            if isinstance(query, str) and query.strip():
                from app.ai.web_search import search_sync

                reference = search_sync(query)
                if reference:
                    log_event(
                        session.session_id,
                        "web_search",
                        query=query[:100],
                        chars=len(reference),
                    )
                    system = system + "\n\n【联网检索参考资料】（用于解释概念和启发创作）\n" + reference + (
                        "\n\n基于上述资料重写 guidance_reply：先用一两句通俗的话解释用户不理解的"
                        "概念，再给出2-3个贴合种子基调的具体创作选项。不要要求用户必须给出明确"
                        "答案——明确告知可以选一个、改一个、说「跳过」或让你先出一版草稿。"
                        "保持其余字段语义不变。"
                    )
                    try:
                        second = asyncio.run(
                            self._provider.chat_json(
                                [
                                    {"role": "system", "content": system},
                                    {"role": "user", "content": text},
                                ]
                            )
                        )
                        if isinstance(second, dict):
                            raw = second
                            log_event(
                                session.session_id, "llm_raw", stage="post_search", response=truncate(raw)
                            )
                    except Exception as e:  # noqa: BLE001 — keep first-pass result
                        log_event(
                            session.session_id,
                            "error",
                            stage="llm_call_post_search",
                            error=str(e)[:300],
                        )

        # ---- knowledge request -> web search -> second pass (D24) ----
        knowledge_hit = False
        if isinstance(raw, dict) and raw.get("knowledge_request"):
            query = raw.get("search_query")
            if isinstance(query, str) and query.strip():
                from app.ai.web_search import search_sync

                reference = search_sync(query)
                if reference:
                    log_event(
                        session.session_id,
                        "web_search",
                        stage="knowledge",
                        query=query[:100],
                        chars=len(reference),
                    )
                    system = system + (
                        "\n\n【联网检索参考资料】（用于回答用户的知识提问）\n"
                    ) + reference + (
                        "\n\n基于上述资料重写 guidance_reply："
                        "先用一两句有据的话直接回答用户的知识问题，"
                        "再给2-3个贴合种子基调的创作选项，最后自然引回当前问题。保持其余字段语义不变。"
                    )
                    try:
                        second = asyncio.run(
                            self._provider.chat_json(
                                [
                                    {"role": "system", "content": system},
                                    {"role": "user", "content": text},
                                ]
                            )
                        )
                        if isinstance(second, dict):
                            raw = second
                            knowledge_hit = True  # 搜索成功 + 二次生效（D24 §1.5）
                            log_event(
                                session.session_id,
                                "llm_raw",
                                stage="post_search",
                                response=truncate(raw),
                            )
                    except Exception as e:  # noqa: BLE001 — keep first-pass result
                        log_event(
                            session.session_id,
                            "error",
                            stage="llm_call_post_search",
                            error=str(e)[:300],
                        )

        result = self._parse(
            raw,
            text,
            recipe=list(getattr(session, "recipe_modules", []) or []) or None,
        )
        if knowledge_hit:
            result.knowledge_used = True  # D24 ①桥接旗标（引擎消费）
        self._open_question_answered = result.open_question_answered
        log_event(
            session.session_id,
            "llm_parsed",
            fills=[f"{f.module}.{f.subfield}={f.value[:80]}" for f in result.fills],
            is_innovative=result.is_innovative,
            innovative_category=result.innovative_category,
        )
        return result

    # ---------- prompt ----------

    @staticmethod
    def _seed_block(session: Any) -> str:
        """Seed context block shared by interview & suggestion prompts."""
        seed_lines = []
        if getattr(session, "seed_name", ""):
            seed_lines.append(
                f"用户选择的种子预设：{session.seed_name}"
                f"（{session.seed_genre}）— {session.seed_description}"
            )
        if getattr(session, "seed_description", "") and not seed_lines:
            seed_lines.append(
                f"记下你的创意了：{session.seed_description}\n"
                "接下来我会一次问你一个问题，帮你把它变成一个完整的世界。"
                "每题都可以自己写、从我给的选项里挑，或者跳过。"
            )
        # E1-Lite T3: 语气锚点模板变量注入（creator_primary 非空且在表中才追加；
        # 空 profile 输出与改动前逐字节相同）。M2：锚点查 Recipe.anchor
        # （数据同源 ANCHOR_BY_TYPE，故事配方锚点随 Recipe 生效）。
        creator_primary = getattr(session, "creator_primary", "")
        recipe = RECIPES.get(creator_primary or "")
        anchor = recipe.anchor if recipe is not None else ""
        if anchor:
            seed_lines.append(f"语气锚点（引导与反馈的基调，务必贯彻）：{anchor}")
        return "\n".join(seed_lines) if seed_lines else "（无，用户从空白开始）"

    def _build_prompt(
        self, module: dict, subfield: dict, session: Any
    ) -> str:
        seed_block = self._seed_block(session)
        answers = getattr(session, "answers", {})
        # G5 泄露修复（M2）：可填字段清单/进度按会话配方渲染——故事会话
        # 的清单只含配方内字段，杜绝配方外世界建构字段的诱导提问通道。
        recipe = list(getattr(session, "recipe_modules", []) or [])
        catalog = _field_catalog(recipe or None)
        # M0→M2 素材槽迁移桥（plan §231）：已归档的 character_sketch 素材
        # 在角色模块（M11）访谈时注入 prompt——LLM 可在用户确认语义后将其
        # 映射进角色字段；不改变门禁/指针（数据注入，非控制流，R2）。
        sketch = (getattr(session, "character_sketch", "") or "").strip()
        sketch_bridge = (
            [
                "3.9 角色素材迁移：以下是之前访谈中归档的角色素材（未经确"
                "认的草料）。当用户本轮输入与这些素材相关（补充/确认/展开），"
                "把对应要点提取进角色模块的合适字段（fills）；无关则忽略本块。",
                "【已归档角色素材】",
                sketch,
            ]
            if sketch and module.get("id") == "角色"
            else []
        )
        graph_lines = graph_digest.graph_digest_block(
            graph_digest.lookup_graph_json(session),
            invited=list(getattr(session, "worldview_invites", []) or []),
        )
        return "\n".join(
            [
                "你是TRPG世界观设计的访谈引导者，正在引导用户构建世界观设定。",
                "",
                "【种子起点】（引导与反馈需与该基调一致）",
                seed_block,
                "",
                "【当前访谈位置】",
                f"模块「{module.get('label', '')}」/ 子字段「{subfield.get('label', '')}」",
                f"参考问题：{subfield.get('question', '')}",
                f"示例：{subfield.get('example', '')}",
                "【字段进度】（已填/总数，判断分配时参考——避免重复填已填字段）",
                _progress_summary(answers, recipe or None),
                "",
                "【用户已确定的内容】",
                _answers_digest(answers),
                # T14/DN5（D20 注入模式）：定稿图谱摘要只读注入——纯代码
                # 确定性装配（零 LLM）；无图时为空列表，prompt 与基线逐字节
                # 一致（零回归）。键域契约：块内无裸 {模块id}. 形态。
                *graph_lines,
                "",
                "【你的任务】",
                "1. 理解用户输入。它可能直接回答当前问题，也可能一口气包含多个字段的设定信息"
                "（例如同时说了名称、类型和核心体验）——把能提取的全部填入 fills。",
                "2. value 用简洁中文提取用户原意，去除口头语；保留用户的关键词。",
                "3. 判断分配：先判断用户输入真正回答或充实了哪些字段——可能是"
                "当前字段、其他模块的字段、或多个字段，只把内容填入它真正属于的"
                "字段。其中当前字段优先（反漏填）：如果输入确实是对当前问题的回答"
                "（即使表述不标准、不像示例、过于简短或口语化），判断后把提取内容填入"
                "当前 module.subfield（可以同时填其他字段）。绝不允许只填其他字段而漏掉"
                "当前字段的回答；但如果输入真正属于其他字段或与世界观无关，则不强制填当前字段。"
                "　　3.1 语义对齐铁律：每条 fill 的 module.subfield 必须与用户原话的实际语义匹配——禁止“语义相近就填进去”。例如：用户说“死亡是自然的常态”，这是对概念的解释，应填 concept，绝不能因为包含“自然”就填入 world_type。每条 fill 必须能用一句话说清：“用户这句话属于该字段，因为……”。",
                # M0 止血：叙事素材归档规则（故事型会话条件注入——差异是数据不是代码）
                *(
                    [
                        "3.8 叙事素材归档：当用户输入是人物、场景、情节片段等叙事素材——"
                        "它不对应【可填字段清单】中任何字段的语义（尤其不是对已答字段的"
                        "修改）时：不生成任何 fills、绝不产生对已填字段的替换/合并提案；"
                        "把素材要点（保留用户关键词与原话质感）写入 story_material 字段，"
                        "guidance_reply 共情确认这段素材已记下。"
                    ]
                    if getattr(session, "creator_primary", "") in STORY_PRIMARY_TYPES
                    else []
                ),
                # M0→M2 素材槽迁移桥（仅角色模块且有归档素材时注入）
                *sketch_bridge,
                "",
                # D23 语义分流规则（3.5 冲突预检升级为 3.5R；保留「冲突预检」
                # 关键词以兼容存量 prompt 契约测试，其余为规范逐字锁定文案）
                "3.5R 语义分流（冲突预检升级版）：fills 落点字段已在"
                "【用户已确定的内容】中有值时，必须判定 relation 并填写："
                "①equivalent（等价/细化：同一意思换述或加深）→ merged_value 必填="
                "融合双方要点后的完整表述（保留用户原话质感，不得丢信息）；"
                "多值字段若只与其中一条等价，同时填 merge_target=那条的开头文字，"
                "merged_value 只融合那一条。②complement（补充：新信息，"
                "不修改旧内容；多值字段的新一段）→ 不需要 merged_value。"
                "③conflict（真矛盾）→ conflict_question 必填=面向用户的人话提问"
                "（呈现新旧语境化对照，给出 替换/都要/先放着 三条路，禁用系统术语）。"
                "④落点为空字段的 fill 不填 relation。判定拿不准时填 conflict"
                "（宁可问不可猜）。",
                "",
                "【不可动清单】（「设定边界」模块中不可变集的锚点，绝对不可覆盖）",
                _immutable_block(answers),
                "",
                "3.6 红线记忆：与【不可动清单】中任何一条冲突的内容，拒绝提取到 fills，"
                "guidance_reply 中必须说明与哪条不可动设定冲突。",
                "3.7 术语转译：面向用户的一切输出（guidance_reply、divergent_question 等）"
                "严禁使用以下术语——拓扑/槽位/派生/枚举/轴向/上游/下游——必须转译为"
                "用户可理解的设定式表述。内部 JSON 字段名不受此限制。",
                "4. 只能填入【可填字段清单】中存在的 module.subfield（module 和 subfield 必须"
                "逐字使用清单中的 id）。",
                "5. 创新判定（从严）：仅当输入是世界观设定、且不属于清单中任何字段能容纳的内容"
                "（全新维度/全新概念）时，is_innovative=true 并给出 innovative_category"
                "（中文短语，作为建议新增的小类名）。普通的名称、概念、描述绝不是创新。",
                # T10（波次一 1.3）规则 6 改写：「引回主题」→「接住-归位-回题」
                # （拍1-4 / ⑨稿 §3 投递话术族·3 式激活；投递式机制设计 §2.1/
                # §5 一期边界——零 schema，落位仍写现有槽）。规则 6.5/7 红线
                # 只读，一字节不动。
                "6. 投递判定（接住-归位-回题）：先看输入是否是【当前问题】的直接"
                "答案——是则正常提取 fills，不做投递。若输入是一个离题的好想法——"
                "不属于当前问题的直接答案，但内容属于【可填字段清单】中某个已有"
                "字段（例：正在问某个模块时，用户突然说出另一个模块的设定或画面）："
                "这是好想法，绝不指责用户离题、严禁说「先聚焦」「等以后再聊」。"
                "三步处理：①接住——一句话确认收到，引用用户原话中的具体关键词；"
                "②归位——从【可填字段清单】中找到该想法所属的字段，生成一条 fill"
                "（module/subfield 逐字用清单 id），并置 delivery=true（投递轮信号，"
                "新增可选键，旧解析器忽略，向前兼容）；③回题——guidance_reply 用"
                "落位确认句式「好想法——我记进【槽位名】了（一句话复述）。回到刚才："
                "【当前问题】」；若该想法与当前模块确有关联，可改用回题桥接句式"
                "「这正好和【当前模块】是一对——」再引回当前问题；找不到关联就直接"
                "温和回题。投递轮的 guidance_reply 结尾附一句撤销护栏：「刚才那笔记"
                "错了地方？说一声，我挪走。」若输入是提问、闲聊或与世界观无关"
                "（不满足本条投递，也不满足 6.5/7）：fills 留空、is_innovative=false，"
                "guidance_reply 回应用户并把话题引回当前问题。",
                "6.5 知识求助判定（优先于规则 6 的提问分支）：如果用户向你提出"
                "领域事实性/知识性问题——期待你提供资料来帮他写故事，而不是在"
                "回答当前问题（如「精神病院里腕带代表什么」「当前最受欢迎的"
                "现代小说女性主角职业是什么」）：置 knowledge_request=true，"
                "并给出一个用于联网检索的中文 search_query（概括用户想知道的"
                "知识点）。此时 fills 必须留空、user_confused=false——严禁把"
                "用户的提问内容当作任何字段的答案记录。",
                "7. 用户困惑判定：如果用户表示不理解当前问题/概念/术语，或明确说"
                "「不知道」「没想法」「不懂」，置 user_confused=true 并给出一个用于联网"
                "检索的中文 search_query（针对用户不理解的概念）。此时 fills 留空，"
                "不要追问用户，等系统提供参考资料后再引导。",
                # M0 止血：偏转规则（全部会话——任何型都可能想先聊别的）
                "7.5 偏转判定：如果用户明确表示不想答当前问题、想先聊别的、或希望"
                "先专注故事主线（如「能先专注于故事吗」「先跳过这个」「先聊聊X」）："
                "置 deflect=true，fills 必须留空（一条也不生成）；guidance_reply 先"
                "共情确认用户的选择，再用一句话自然引向下一个话题（贴合语气锚点基调，"
                "不纠缠当前问题）。",
                # D20 动态模块调用（2026-09-25 产品方裁决）：世界建构域目录 +
                # 提议指令（无侵入数据注入——目录只描述领域，不改变可填清单）
                "7.6 动态模块调用：用户在对话中**提及**某领域世界观设定内容时"
                "（不是顺带出现的单个词，而是表达了该领域的设定内容），对照"
                "【世界建构模块域目录】把对应模块 id 写入 worldview_invites "
                "数组（可多个；本轮无提及则留空数组）：",
                "【世界建构模块域目录】",
                *[
                    f"　　{mid}：{desc}"
                    for mid, desc in WORLDVIEW_DOMAIN_CATALOG.items()
                ],
                "　　注意：这是提议信号，由系统确定性校验后才生效；你不得在 "
                "guidance_reply 中承诺加入任何模块，也不得因此改变 fills 行为。",
                "　　契约说明：worldview_invites 为新增可选键，旧解析器忽略未知"
                "键，向前兼容（G6b/M0 偏转先例，D20）。",
                "8. guidance_reply（中文，总共不超过三句话）：先用一句话确认已记录的"
                "设定——引用用户输入中的具体关键词，给出有内容的确认而非套话；"
                "再用一句话衔接收尾即可。**问句单源铁律：guidance_reply 中严禁出现任何"
                "新的疑问句或新话题——下一个问题完全由系统的结构化问句（下方提示卡）承担，"
                "你不得自行提问、不得自行引入新字段或新模块的话题。**仅当用户明显困惑时，"
                "可以用一句话引导用户看下方的当前问题。",
                "9. 发散引导（访谈引导者的核心职责，当 fills 非空时执行）：从"
                "【可填字段清单】中挑一个尚未出现在【用户已确定的内容】里、但与"
                "本次输入存在设定关联的字段，构造一个发散追问。要求："
                "a) 追问必须锚定用户刚写下的具体设定（引用其关键词），不得是放在"
                "任何世界观里都成立的泛泛模板问题；"
                "b) 追问指向设定间的推导关系——例如用户写力量来源是「古神遗骸」，"
                "可问「这些遗骸散落在地表时，当地文明把它们当圣地还是矿脉？」"
                "（这会牵引文明与社会的核心价值）；写核心冲突时可问它在历史时间线"
                "上爆发为哪个关键节点；"
                "c) 追问以单个问句存入 divergent_question 字段，同时在 guidance_reply"
                "结尾以邀请口吻自然带出（如「顺便一提：……」），不替换、不阻塞当前"
                "问题的推进；",
                "d) 第6条（提问/闲聊/无关）或第7条（用户困惑）场景下不做发散，"
                "divergent_question 为 null。",
                "",
                *self._pending_question_block(),
                # 方向A一期（T2）：默认示例生成规则块 8.6——编号衔接 8.5
                # 之后；8.5 本体与编号零改动（红线 2）。生成任务段纪律逐字
                # 搬运 suggest_examples prompt（L601-633 先例），不新造文案。
                "8.6 默认示例生成：除理解用户输入外，同时为【当前问题】所指字段"
                "生成 3 个具体的中文示例方向——必须贴合【种子起点】基调、"
                "与【用户已确定的内容】兼容、彼此风格差异化、每个不超过 40 字。"
                "故事向会话：示例必须从用户已答的剧情、角色、情感线索延伸"
                "（引用用户已答内容里的具体关键词），严禁输出势力、政治、阵营类"
                "世界建构模板示例。"
                "示例只服务于【当前问题】——示例序号仅对当前题的示例有效，"
                "不得为其它题生成示例、也不得把示例序号与别的题目关联"
                "（T10 疑因(b) 核正：跨题示例一律无效）。",
                # 方向A一期（T6）：示例风格锚点（条件注入——creator_primary
                # 命中 ANCHOR_BY_TYPE 才追加；锚点原文逐字引用，不改写）。
                *(
                    [
                        f"示例风格贴合该冲动类型的语气锚点："
                        f"{ANCHOR_BY_TYPE[session.creator_primary]}"
                    ]
                    if getattr(session, "creator_primary", "") in ANCHOR_BY_TYPE
                    else []
                ),
                "　　用户回复若引用示例序号（如「选2吧」「把1和3揉一起」"
                "「第1点对」），结合示例内容理解并生成对应 fills，不要当作纯数字。",
                "　　示例必须是陈述句；guidance_reply 与示例中严禁出现任何新的"
                "疑问句——全回复唯一疑问句仍是 8.5 规定的当前问题本身。",
                "",
                "【可填字段清单】",
                catalog,
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"fills": [{"module": "...", "subfield": "...", "value": "..."}],',
                ' "guidance_reply": "...", "is_innovative": false, "innovative_category": null,',
                ' "user_confused": false, "knowledge_request": false, "search_query": null, "divergent_question": null,',
                ' "deflect": false, "story_material": null, "open_question_answered": null,',
                ' "worldview_invites": [], "delivery": false, "examples": ["...", "...", "..."]}',
            ]
        )

    def _pending_question_block(self) -> list[str]:
        """C7: 待问开放问题规则块（无待问时返回空）。

        单问句铁律：一次只问一条（最老优先）；提案卡片在场时由
        chat 端点直接不注入本块（挂起）。
        """
        if not self._pending_open_question:
            return []
        return [
            "8.5 待问开放问题（系统指定，最老优先，一次只问一条）：存在一条"
            "悬而未决的开放问题待你向用户问出：",
            f"【待问】id={self._pending_open_question.get('id', '')}，"
            f"问句：{self._pending_open_question.get('question', '')}",
            "　　a) 在 guidance_reply 结尾用邀请口吻自然问出这一条（只此一条，"
            "严禁追加任何其他疑问句——单问句铁律）；",
            "　　b) 若用户本轮输入正是对该问题的回答，把提取的答案写入 "
            'open_question_answered 字段（{"id": 问题id, "answer": 用户原话要点}）；',
            "　　c) 若判断本轮应先处理其他事项（如用户困惑、话题未完），本轮挂起"
            "不问，该字段保持原样等待下一轮；",
            "　　d) 问出后不自行追问，等待用户回答。",
            "",
        ]

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]:
        """Generate 2-3 seed-referenced example answers for a subfield.

        Used by the anti-stall guard: when the user is stuck on a field,
        the LLM proposes concrete options grounded in the seed context.
        Returns [] on any failure — callers degrade to raw-text fill.
        """
        module = get_module(module_id) or {}
        subfield = get_subfield(module_id, subfield_id) or {}
        answers = getattr(session, "answers", {})
        system = "\n".join(
            [
                "你是TRPG世界观设计的访谈引导者。用户在某个字段上卡住了，"
                "需要你给出具体的示例答案帮助其继续。",
                "",
                "【种子起点】（示例风格必须贴合该基调）",
                self._seed_block(session),
                "",
                "【目标字段】",
                f"模块「{module.get('label', module_id)}」"
                f"/ 子字段「{subfield.get('label', subfield_id)}」",
                f"参考问题：{subfield.get('question', '')}",
                f"参考示例：{subfield.get('example', '')}",
                "",
                "【用户已确定的内容】（示例需与之兼容）",
                _answers_digest(answers),
                "",
                "【你的任务】",
                "参考种子基调与已确定的设定，为该字段生成3个具体的中文示例答案，"
                "每个不超过40字，彼此风格差异化。不要解释，只给示例。",
                # M0 止血：故事型会话降级建议换料（条件注入——差异是数据不是代码）
                *(
                    [
                        "故事向会话：示例必须从【用户已确定的内容】中的剧情、角色、"
                        "情感线索延伸提问方向（引用用户已答内容里的具体关键词），"
                        "严禁输出势力、政治、阵营类世界建构模板示例。"
                    ]
                    if getattr(session, "creator_primary", "") in STORY_PRIMARY_TYPES
                    else []
                ),
                # 方向A一期（T6）：示例风格锚点（条件注入，同 _build_prompt 8.6 处）。
                *(
                    [
                        f"示例风格贴合该冲动类型的语气锚点："
                        f"{ANCHOR_BY_TYPE[session.creator_primary]}"
                    ]
                    if getattr(session, "creator_primary", "") in ANCHOR_BY_TYPE
                    else []
                ),
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"examples": ["...", "...", "..."]}',
            ]
        )
        try:
            raw = asyncio.run(self._provider.chat_json([{"role": "system", "content": system}]))
        except Exception:  # noqa: BLE001 — degrade, never raise
            return []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        if not isinstance(raw, dict):
            return []
        items = raw.get("examples")
        if not isinstance(items, list):
            return []
        out = [s.strip() for s in items if isinstance(s, str) and s.strip()]
        return out[:3]

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:
        """Last-resort judgment for the anti-stall guard (stall >= 3).

        The user has repeatedly failed to answer the current subfield.
        Read the latest input and judge strictly whether it fills ANY
        legal field. Never blind-fill: no belongs-to-any-field judgment,
        no recording.
        """
        module = get_module(session.current_module) or {}
        subfield = get_subfield(session.current_module, session.current_subfield) or {}
        seed_block = self._seed_block(session)
        answers = getattr(session, "answers", {})
        system = "\n".join(
            [
                "你是TRPG世界观设计的访谈引导者。用户在当前字段上已连续多轮"
                "未能给出有效回答，需要你做最后一次严格判定。",
                "",
                "【种子起点】",
                seed_block,
                "",
                "【卡住的位置】",
                f"模块「{module.get('label', '')}」/ 子字段「{subfield.get('label', '')}」",
                f"参考问题：{subfield.get('question', '')}",
                "",
                "【用户已确定的内容】",
                _answers_digest(answers),
                "",
                "【你的任务】",
                "1. 严格判断用户最新输入是否真正回答或充实了【可填字段清单】中的"
                "任何字段（包括当前字段）。宁可漏填，不可错填。",
                "2. 如果确有归属字段：把提取内容填入那些字段"
                "（value 为简洁中文，保留用户关键词）。",
                "3. 如果无法判断归属（闲聊、提问、含糊其辞）：fills 留空、"
                "is_innovative=false，guidance_reply 引导用户：选择一个示例序号、"
                "换种说法回答、或回复「跳过」。",
                "4. 创新判定与常规访谈相同（从严）：仅当输入是世界观设定且不属于"
                "清单中任何字段能容纳的内容时，is_innovative=true 并给出"
                "innovative_category。",
                "5. 只能填入【可填字段清单】中存在的 module.subfield"
                "（module 和 subfield 必须逐字使用清单中的 id）。",
                "",
                "【可填字段清单】",
                _field_catalog(
                    list(getattr(session, "recipe_modules", []) or []) or None
                ),
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"fills": [{"module": "...", "subfield": "...", "value": "..."}],',
                ' "guidance_reply": "...", "is_innovative": false, "innovative_category": null}',
            ]
        )
        try:
            raw = asyncio.run(
                self._provider.chat_json(
                    [
                        {"role": "system", "content": system},
                        {"role": "user", "content": text},
                    ]
                )
            )
        except Exception as e:  # noqa: BLE001 — degrade, never crash the session
            log_event(session.session_id, "error", stage="llm_call", error=str(e)[:300])
            raise RuntimeError(f"LLM forced_allocate failed: {e}") from e
        result = self._parse(
            raw,
            text,
            recipe=list(getattr(session, "recipe_modules", []) or []) or None,
        )
        log_event(
            session.session_id,
            "llm_parsed",
            stage="forced_allocate",
            fills=[f"{f.module}.{f.subfield}={f.value[:80]}" for f in result.fills],
            is_innovative=result.is_innovative,
            innovative_category=result.innovative_category,
        )
        return result

    # ---------- parse & validate ----------

    def classify_confirm_intent(
        self, old_value: str, new_value: str, user_reply: str
    ) -> str:
        """D23⑧ 提案回复一句话分类（confirm 免卡片通道，消费侧接线归后续）。

        返回闭集逐字锁定："replace"|"merge"|"drop"|"other"，不允许添加或
        修改。异常向上传播（DegradingInterviewer 侧统一降级 "other"）。
        """
        system = "\n".join(
            [
                "你是世界观访谈助手。用户此前对一个设定修改提案收到三条选项：",
                "替换（replace）/ 合并（merge，同一条里都保留）/ 放弃（drop）。",
                "现在判断用户的回复属于哪一种意图。只输出一个词。",
                "",
                f"【旧设定】{old_value}",
                f"【新设定】{new_value}",
                f"【用户回复】{user_reply}",
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"intent": "replace|merge|drop|other"}',
            ]
        )
        raw = asyncio.run(
            self._provider.chat_json([{"role": "system", "content": system}])
        )
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            return "other"
        intent = raw.get("intent")
        return intent if intent in ("replace", "merge", "drop", "other") else "other"

    def _parse(
        self,
        raw: Any,
        text: str,
        recipe: list[str] | None = None,
        valid_keys: set[str] | None = None,
    ) -> InterviewResult:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raise RuntimeError("LLM returned non-JSON") from None
        if not isinstance(raw, dict):
            raise RuntimeError("LLM returned unexpected shape")

        # M2 G5：fills 合法性 = 配方并集（None = 全集，default 逐字节不变）。
        # 显式 valid_keys 优先（契约测试/调用方直给合法键集）。
        keys = valid_keys if valid_keys is not None else set(all_subfield_keys(recipe))
        fills: list[InterviewFill] = []
        for item in raw.get("fills") or []:
            if not isinstance(item, dict):
                continue
            module, sub, value = (
                item.get("module"),
                item.get("subfield"),
                item.get("value"),
            )
            if not all(isinstance(x, str) and x for x in (module, sub, value)):
                continue
            if f"{module}.{sub}" not in keys:
                continue  # 铁律：不允许清单外字段
            conflict = item.get("conflict_note")
            # D23 语义分流可选键（3.5R）：缺省 None = 现行拦截行为逐字节不变。
            relation = item.get("relation")
            merged_value = item.get("merged_value")
            merge_target = item.get("merge_target")
            conflict_question = item.get("conflict_question")

            def _opt_str(x: Any) -> str | None:
                return x.strip() if isinstance(x, str) and x.strip() else None

            fills.append(
                InterviewFill(
                    module=module,
                    subfield=sub,
                    value=value.strip(),
                    conflict_note=conflict.strip() if isinstance(conflict, str) and conflict.strip() else None,
                    relation=_opt_str(relation),
                    merged_value=_opt_str(merged_value),
                    merge_target=_opt_str(merge_target),
                    conflict_question=_opt_str(conflict_question),
                )
            )

        reply = raw.get("guidance_reply")
        innovative = bool(raw.get("is_innovative"))
        category = raw.get("innovative_category")
        divergent = raw.get("divergent_question")

        # C7: open_question_answered 解析（{"id","answer"}）
        oqa_raw = raw.get("open_question_answered")
        open_question_answered: dict | None = None
        if isinstance(oqa_raw, dict):
            qid = oqa_raw.get("id")
            ans = oqa_raw.get("answer")
            if (
                isinstance(qid, str)
                and qid.strip()
                and isinstance(ans, str)
                and ans.strip()
            ):
                open_question_answered = {"id": qid.strip(), "answer": ans.strip()}

        # M0 止血：偏转标记 + 叙事素材解析（可选键，向前兼容豁免）。
        deflect = bool(raw.get("deflect"))
        if deflect:
            fills = []  # 偏转不生成 fills（prompt 规则之外的确定性兜底）
        material_raw = raw.get("story_material")
        story_material = (
            material_raw.strip()
            if isinstance(material_raw, str) and material_raw.strip()
            else None
        )

        # D20：worldview_invites 解析（仅提取字符串候选；闭集/去重/上限等
        # 确定性校验在 guide_engine 消费侧——LLM 不进控制流）。
        invites_raw = raw.get("worldview_invites")
        worldview_invites = (
            [s.strip() for s in invites_raw if isinstance(s, str) and s.strip()]
            if isinstance(invites_raw, list)
            else []
        )

        # 方向A一期（T2）：examples 解析——非 list / 元素非 str / 空 →
        # []（静默降级，不重试不报错；模式照抄 worldview_invites/
        # suggest_examples 先例）。空 = 引擎侧零追加（旧行为逐字节）。
        examples_raw = raw.get("examples")
        examples = (
            [s.strip() for s in examples_raw if isinstance(s, str) and s.strip()]
            if isinstance(examples_raw, list)
            else []
        )

        # T10（波次一 1.3）：投递意图键解析（additive 布尔，缺省 False =
        # 存量行为零扰动）。投递轮不做确定性兜底改写——fills 已在规则 6
        # 约束下落清单内既有槽；无槽可落时 LLM 置 delivery=true 且 fills
        # 留空（温和回题），解析侧保持原样透传。
        delivery = bool(raw.get("delivery"))

        return InterviewResult(
            fills=fills,
            guidance_reply=reply if isinstance(reply, str) and reply else "已记录。",
            is_innovative=innovative,
            innovative_category=category if isinstance(category, str) else None,
            divergent_question=(
                divergent.strip()
                if isinstance(divergent, str) and divergent.strip()
                else None
            ),
            open_question_answered=open_question_answered,
            deflect=deflect,
            story_material=story_material,
            worldview_invites=worldview_invites,
            examples=examples,
            delivery=delivery,
        )


class DegradingInterviewer:
    """Wrapper: LLM first; on failure ask the user to retry — never
    record text into a field without LLM judgment (blind-recording
    fix, 2026-08-26)."""

    def __init__(self, inner: Interviewer) -> None:
        self._inner = inner

    def interview(self, session: Any, text: str) -> InterviewResult:
        try:
            return self._inner.interview(session, text)
        except Exception:  # noqa: BLE001
            return InterviewResult(
                fills=[],
                guidance_reply=(
                    "LLM 服务暂时不可用，这条先不记录——请稍后重试，"
                    "或换种说法再说一次。"
                ),
                is_innovative=False,
            )

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:
        try:
            return self._inner.forced_allocate(session, text)
        except Exception:  # noqa: BLE001
            return InterviewResult(
                fills=[],
                guidance_reply=(
                    "LLM 服务暂时不可用，这条先不记录——请稍后重试、"
                    "换种说法，或回复「跳过」。"
                ),
                is_innovative=False,
            )

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]:
        try:
            return self._inner.suggest_examples(session, module_id, subfield_id)
        except Exception:  # noqa: BLE001
            return []

    # ---- D23: 提案回复一句话分类（降级模式同 suggest_examples） ----

    def classify_confirm_intent(
        self, old_value: str, new_value: str, user_reply: str
    ) -> str:
        try:
            return self._inner.classify_confirm_intent(old_value, new_value, user_reply)
        except Exception:  # noqa: BLE001 — degrade, never crash
            return "other"

    # ---- C7: 待问开放问题（委托 inner；inner 不支持时静默降级） ----

    def set_pending_open_question(self, question: dict) -> None:
        setter = getattr(self._inner, "set_pending_open_question", None)
        if setter is not None:
            setter(question)

    def take_open_question_answered(self) -> dict | None:
        getter = getattr(self._inner, "take_open_question_answered", None)
        return getter() if getter is not None else None
