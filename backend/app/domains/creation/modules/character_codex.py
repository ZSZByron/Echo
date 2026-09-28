# -*- coding: utf-8 -*-
"""人物志渲染器（D22 · C——角色数据小说化渲染）——五件套模具复用。

证据：docs/decision-log.md D22①「人物志（角色数据小说化渲染）」逐字；
模具母本 ``main_module.py``（主模组文字版，finalize 八步 + 九节树同构）。

五件套落位：
- 冻结章节树：M11 角色模块六字段（identity/desire/flaw/key_relations/
  arc_direction/character_visual，story_modules.M11_CHARACTER 定版）
  + 世界本体.reality_rule 语境章——顺序即契约。
- 信号键绑定：``角色.*`` 与 T7 OUTPUT_MODULES 注册（character_codex
  signal_requirements）一致；缺料章正文留白，诚实不编造。
- LLM 导语层（**本件特有**）：导语 prompt 强调**小说化渲染**（D22①
  逐字）——只产渲染语气导语，仍守「只产导语、失败降级」契约。
- 装配/降级/序列化：答案原文直投，LLM 永不改写用户引述事实；
  provider 缺席/失败/形状不符 → 确定性骨架 + ledger 披露
  ``character_codex_degraded``——零 LLM key 免费线可跑通。
- 溯源：C 字 issuance（graph_code_issuer stage="C"）。
  语义边界：C(人物志) ≠ TC(角色投影模板 character_projector)。

模具纪律：无模具外 pattern、无编造、无端点。
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field

# ── 冻结章节树（M11 字段 + 语境章；顺序即契约）────────────────────────

CODEX_CHAPTER_HEADINGS: tuple[str, ...] = (
    "身世", "心之所欲", "暗面缺陷", "关键关系",
    "弧光方向", "视觉锚点", "世界法则",
)

#: 每章 ← 答案信号键映射（确定性装配；缺料章正文留白，诚实不编造）。
_CHAPTER_SIGNALS: dict[str, tuple[str, ...]] = {
    "身世": ("角色.identity",),
    "心之所欲": ("角色.desire",),
    "暗面缺陷": ("角色.flaw",),
    "关键关系": ("角色.key_relations",),
    "弧光方向": ("角色.arc_direction",),
    "视觉锚点": ("角色.character_visual",),
    "世界法则": ("世界本体.reality_rule",),
}

#: LLM 导语 prompt——**小说化语气**（D22①「角色数据小说化渲染」逐字落位）。
#: 只产导语（渲染语气），结构（章节树/答案原文）由确定性代码装配。
_CODEX_COMPILE_PROMPT = """你是小说编辑。基于以下角色信号，为人物志
输出渲染导语（只产文案，不产结构数值）。导语要求**小说化**：以叙事
语气渲染人物质感，1-2 句，不得改写或复述信号原文中的事实。
{"codex_fantasy": "一句话人物核心意象",
 "chapters": {"{章标题}": "该章小说化导语（1-2 句）", ...}}
章标题必须是以下七个之一，不得增删改：
{headings}

角色信号：
{signals}"""


class CodexChapter(BaseModel):
    """人物志章节节点（模具：ModuleDocSection 同构）。"""
    heading: str
    level: int
    body: str = ""


class CharacterCodex(BaseModel):
    """人物志文档——角色数据小说化渲染的直接载体（D22①）。"""
    title: str
    codex_fantasy: str
    chapters: list[CodexChapter] = Field(default_factory=list)
    graph_code: str
    upstream_graph_code: str
    generated_at: str = ""
    used_stale: bool = False
    # D21⑬/T15：可选 α 版本可见标记（见 a1.draft_version；定稿/存量 = None，
    # 零迁移；α 绝不进持久层）。
    version_label: str | None = None
    upstream_ledger: list[dict[str, Any]] = Field(default_factory=list)


def render_markdown(doc: CharacterCodex) -> str:
    """单向序列化：文档 → Markdown（零加工可读，模具：main_module 同构）。"""
    lines = [f"# {doc.title}", "", f"> {doc.codex_fantasy}", ""]
    for ch in doc.chapters:
        lines.append(f"{'#' * (ch.level + 1)} {ch.heading}")
        lines.append("")
        if ch.body:
            lines.append(ch.body)
            lines.append("")
    lines.append("---")
    lines.append(f"溯源：{doc.graph_code} ← {doc.upstream_graph_code}")
    return "\n".join(lines)


def _skeleton_chapter_body(heading: str, answers: dict[str, str]) -> str:
    """确定性骨架：映射答案原文直投（不经过任何生成）。"""
    from app.domains.creation.seed.a1_question_tree import MODULES
    from app.domains.creation.seed.story_modules import STORY_MODULES

    labels: dict[str, str] = {}
    for m in (*MODULES, *STORY_MODULES):
        for f in m["fields"]:
            labels[f"{m['id']}.{f['id']}"] = f["label"]

    lines = []
    for key in _CHAPTER_SIGNALS.get(heading, ()):
        value = (answers.get(key) or "").strip()
        if value:
            lines.append(f"- {labels.get(key, key)}：{value}")
    return "\n".join(lines)


def _as_coro(awaitable: Any) -> Any:
    """Wrap an awaitable so ``asyncio.run`` receives a coroutine (typing)."""

    async def _run() -> Any:
        return await awaitable

    return _run()


def codex_compile_copy(provider: Any, answers: dict[str, str]) -> dict | None:
    """codex_compile —— LLM 导语单生产点（模具：module_compile 同构）。

    只请求小说化导语（codex_fantasy + 章导语）；任何失败（provider
    缺席/网络/形状不符）返回 None，由调用方走确定性骨架。永不抛出。
    """
    if provider is None:
        return None
    try:
        signals = "\n".join(
            f"- {k}: {v}" for k, v in sorted(answers.items()) if v.strip()
        )
        messages = [{
            "role": "user",
            "content": _CODEX_COMPILE_PROMPT.replace(
                "{headings}", "、".join(CODEX_CHAPTER_HEADINGS),
            ).replace("{signals}", signals or "（无）"),
        }]
        res = provider.chat_json(messages)
        if inspect.isawaitable(res):
            res = asyncio.run(_as_coro(res))
        raw = res
        if not isinstance(raw, dict):
            return None
        fantasy = raw.get("codex_fantasy")
        chapters = raw.get("chapters")
        if not isinstance(fantasy, str) or not fantasy.strip():
            return None
        if not isinstance(chapters, dict):
            chapters = {}
        clean = {
            h: str(chapters[h]).strip()
            for h in CODEX_CHAPTER_HEADINGS
            if isinstance(chapters.get(h), str) and chapters[h].strip()
        }
        return {"codex_fantasy": fantasy.strip(), "chapters": clean}
    except Exception:  # noqa: BLE001 — LLM 永不阻塞主路径（模具：D2-③）
        return None


def compile_codex(
    answers: dict[str, str],
    *,
    character_name: str,
    graph_code: str,
    upstream_graph_code: str,
    provider: Any = None,
    used_stale: bool = False,
    upstream_ledger: list[dict[str, Any]] | None = None,
) -> tuple[CharacterCodex, list[dict[str, Any]]]:
    """确定性装配七章人物志；LLM（codex_compile 单点）只叠加小说化导语。

    返回 (document, ledger_entries)；LLM 缺席/失败 → 骨架兜底并披露
    ``character_codex_degraded``（诚实可观测，零 LLM key 免费线可用）。
    """
    copy = codex_compile_copy(provider, answers)
    ledger: list[dict[str, Any]] = []
    if copy is None:
        fantasy = (
            f"{character_name}：一份角色数据小说化渲染（确定性骨架版）"
            if character_name.strip()
            else "角色数据小说化渲染（确定性骨架版）"
        )
        degraded = True
    else:
        fantasy = copy["codex_fantasy"]
        degraded = False

    chapters = [
        CodexChapter(heading=heading, level=2,
                     body=_skeleton_chapter_body(heading, answers))
        for heading in CODEX_CHAPTER_HEADINGS
    ]
    if copy is not None:
        # LLM 导语只作渲染语气叠加，结构（章树/标题/答案原文）不动——
        # 用户引述事实永不被改写（D22①：数据 = 用户答案直投）
        for ch in chapters:
            intro = copy["chapters"].get(ch.heading)
            if intro:
                ch.body = f"{intro}\n\n{ch.body}" if ch.body else intro

    if degraded:
        from app.domains.creation.a1.warning_ledger import entry as ledger_entry
        ledger.append(dict(ledger_entry(
            "finalize",
            "character_codex_degraded：LLM 不可用，人物志取确定性骨架"
            "（答案原文直投，免费线可跑通）",
        )))

    doc = CharacterCodex(
        title=character_name or "人物志",
        codex_fantasy=fantasy,
        chapters=chapters,
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        used_stale=used_stale,
        upstream_ledger=list(upstream_ledger or []),
    )
    return doc, ledger
