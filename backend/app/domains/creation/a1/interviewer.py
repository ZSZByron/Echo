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
from app.domains.creation.a1.interaction_log import log_event, truncate
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    get_module,
    get_subfield,
)


class InterviewFill(BaseModel):
    """One structured write: put value into module.subfield."""

    module: str
    subfield: str
    value: str
    conflict_note: str | None = None


class Proposal(BaseModel):
    """A proposed change to an already-filled field."""

    module: str
    subfield: str
    old: str
    new: str
    conflict_note: str | None = None
    merge_preview: str = ""

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
        self._pending_open_question: dict | None = None
        self.calls = 0
        self.suggest_calls = 0
        self.forced_calls = 0

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
        )

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]:
        self.suggest_calls += 1
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


def _progress_summary(answers: dict[str, str]) -> str:
    """Compact one-line-per-module progress: module: filled/total."""
    lines = []
    for m in MODULES:
        mid = m["id"]
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


def _field_catalog() -> str:
    """One line per subfield: 'module.subfield: label — question'."""
    lines = []
    for m in MODULES:
        for f in m["fields"]:
            lines.append(f"{m['id']}.{f['id']}: {f['label']} — {f['question']}")
    return "\n".join(lines)


_MAX_ANSWER_DIGEST = 12


def _answers_digest(answers: dict[str, str]) -> str:
    items = [
        f"{k} = {v[:40]}" for k, v in list(answers.items())[:_MAX_ANSWER_DIGEST] if v
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
        self._catalog = _field_catalog()
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

        result = self._parse(raw, text)
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
            seed_lines.append(f"用户的初始创意：{session.seed_description}")
        return "\n".join(seed_lines) if seed_lines else "（无，用户从空白开始）"

    def _build_prompt(
        self, module: dict, subfield: dict, session: Any
    ) -> str:
        seed_block = self._seed_block(session)
        answers = getattr(session, "answers", {})
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
                _progress_summary(answers),
                "",
                "【用户已确定的内容】",
                _answers_digest(answers),
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
                "",
                "3.5 冲突预检：生成 fills 前逐条对照【用户已确定的内容】，检查是否存在"
                "矛盾（新内容与已确定内容直接冲突）、窄化（用个例替代通例）或"
                "重叠（用实例冒充类型）的情况。若存在冲突，该 fill 必须标记 "
                "conflict_note 字段（用世界观语言描述冲突原因），value 仍按用户原意提取。",
                "",
                "【不可动清单】（设定边界.不可变集中的锚点，绝对不可覆盖）",
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
                "6. 如果输入是提问、闲聊或与世界观无关：fills 留空、is_innovative=false，"
                "guidance_reply 回应用户并把话题引回当前问题。",
                "7. 用户困惑判定：如果用户表示不理解当前问题/概念/术语，或明确说"
                "「不知道」「没想法」「不懂」，置 user_confused=true 并给出一个用于联网"
                "检索的中文 search_query（针对用户不理解的概念）。此时 fills 留空，"
                "不要追问用户，等系统提供参考资料后再引导。",
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
                "【可填字段清单】",
                self._catalog,
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"fills": [{"module": "...", "subfield": "...", "value": "..."}],',
                ' "guidance_reply": "...", "is_innovative": false, "innovative_category": null,',
                ' "user_confused": false, "search_query": null, "divergent_question": null,',
                ' "open_question_answered": null}',
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
                self._catalog,
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
        result = self._parse(raw, text)
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

    def _parse(self, raw: Any, text: str) -> InterviewResult:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raise RuntimeError("LLM returned non-JSON") from None
        if not isinstance(raw, dict):
            raise RuntimeError("LLM returned unexpected shape")

        valid_keys = set(all_subfield_keys())
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
            if f"{module}.{sub}" not in valid_keys:
                continue  # 铁律：不允许清单外字段
            conflict = item.get("conflict_note")
            fills.append(
                InterviewFill(
                    module=module,
                    subfield=sub,
                    value=value.strip(),
                    conflict_note=conflict.strip() if isinstance(conflict, str) and conflict.strip() else None,
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

    # ---- C7: 待问开放问题（委托 inner；inner 不支持时静默降级） ----

    def set_pending_open_question(self, question: dict) -> None:
        setter = getattr(self._inner, "set_pending_open_question", None)
        if setter is not None:
            setter(question)

    def take_open_question_answered(self) -> dict | None:
        getter = getattr(self._inner, "take_open_question_answered", None)
        return getter() if getter is not None else None
