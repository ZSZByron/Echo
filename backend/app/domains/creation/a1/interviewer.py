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


class InterviewResult(BaseModel):
    """LLM understanding of one user message."""

    fills: list[InterviewFill] = Field(default_factory=list)
    guidance_reply: str = ""
    is_innovative: bool = False
    innovative_category: str | None = None
    divergent_question: str | None = None


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
    ) -> None:
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.is_innovative = is_innovative
        self.innovative_category = innovative_category
        self.raise_error = raise_error
        self._examples = examples
        self._forced_allocate_result = forced_allocate_result
        self.calls = 0
        self.suggest_calls = 0
        self.forced_calls = 0

    def interview(self, session: Any, text: str) -> InterviewResult:
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("llm unavailable")
        return InterviewResult(
            fills=self.fills,
            guidance_reply=self.guidance_reply,
            is_innovative=self.is_innovative,
            innovative_category=self.innovative_category,
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
                "当前字段的回答；但如果输入真正属于其他字段或与世界观无关，则不强制填当前字段。",
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
                "8. guidance_reply（中文，总共不超过四句话）：先用一句话确认已记录的"
                "设定——引用用户输入中的具体关键词，给出有内容的确认而非套话；"
                "再自然过渡到下一话题或聚焦当前问题。不得反复重申同一个问题——"
                "仅当输入确实回答了当前问题时才确认并推进，否则引导用户聚焦当前问题。",
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
                "【可填字段清单】",
                self._catalog,
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"fills": [{"module": "...", "subfield": "...", "value": "..."}],',
                ' "guidance_reply": "...", "is_innovative": false, "innovative_category": null,',
                ' "user_confused": false, "search_query": null, "divergent_question": null}',
            ]
        )

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
            fills.append(InterviewFill(module=module, subfield=sub, value=value.strip()))

        reply = raw.get("guidance_reply")
        innovative = bool(raw.get("is_innovative"))
        category = raw.get("innovative_category")
        divergent = raw.get("divergent_question")

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
