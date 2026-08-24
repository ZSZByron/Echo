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


class Interviewer(Protocol):
    def interview(self, session: Any, text: str) -> InterviewResult: ...


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
    ) -> None:
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.is_innovative = is_innovative
        self.innovative_category = innovative_category
        self.raise_error = raise_error
        self.calls = 0

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
            raise RuntimeError(f"LLM interview failed: {e}") from e
        return self._parse(raw, text)

    # ---------- prompt ----------

    def _build_prompt(
        self, module: dict, subfield: dict, session: Any
    ) -> str:
        # Seed context: the preset (or custom idea) the user started from.
        seed_lines = []
        if getattr(session, "seed_name", ""):
            seed_lines.append(
                f"用户选择的种子预设：{session.seed_name}"
                f"（{session.seed_genre}）— {session.seed_description}"
            )
        if getattr(session, "seed_description", "") and not seed_lines:
            seed_lines.append(f"用户的初始创意：{session.seed_description}")
        seed_block = "\n".join(seed_lines) if seed_lines else "（无，用户从空白开始）"
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
                "",
                "【用户已确定的内容】",
                _answers_digest(answers),
                "",
                "【你的任务】",
                "1. 理解用户输入。它可能直接回答当前问题，也可能一口气包含多个字段的设定信息"
                "（例如同时说了名称、类型和核心体验）——把能提取的全部填入 fills。",
                "2. value 用简洁中文提取用户原意，去除口头语；保留用户的关键词。",
                "3. 只能填入【可填字段清单】中存在的 module.subfield（module 和 subfield 必须"
                "逐字使用清单中的 id）。",
                "4. 创新判定（从严）：仅当输入是世界观设定、且不属于清单中任何字段能容纳的内容"
                "（全新维度/全新概念）时，is_innovative=true 并给出 innovative_category"
                "（中文短语，作为建议新增的小类名）。普通的名称、概念、描述绝不是创新。",
                "5. 如果输入是提问、闲聊或与世界观无关：fills 留空、is_innovative=false，"
                "guidance_reply 回应用户并把话题引回当前问题。",
                "6. guidance_reply：用不超过两句话确认已记录的设定并自然过渡"
                "（可结合用户已填内容给出专业反馈，中文）。",
                "",
                "【可填字段清单】",
                self._catalog,
                "",
                "返回严格JSON（不要输出其他内容）：",
                '{"fills": [{"module": "...", "subfield": "...", "value": "..."}],',
                ' "guidance_reply": "...", "is_innovative": false, "innovative_category": null}',
            ]
        )

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

        return InterviewResult(
            fills=fills,
            guidance_reply=reply if isinstance(reply, str) and reply else "已记录。",
            is_innovative=innovative,
            innovative_category=category if isinstance(category, str) else None,
        )


class DegradingInterviewer:
    """Wrapper: LLM first; on failure, store text into the current
    subfield directly (a name is just a name — never an innovation)."""

    def __init__(self, inner: Interviewer) -> None:
        self._inner = inner

    def interview(self, session: Any, text: str) -> InterviewResult:
        try:
            return self._inner.interview(session, text)
        except Exception:  # noqa: BLE001
            return InterviewResult(
                fills=[
                    InterviewFill(
                        module=session.current_module,
                        subfield=session.current_subfield,
                        value=text.strip(),
                    )
                ],
                guidance_reply="（离线模式）已直接记录你的输入。",
                is_innovative=False,
            )
