# -*- coding: utf-8 -*-
"""世界圣经（M3 产出模块 · D22①）——五件套模具逐字复用（B 信）。

证据：``docs/decision-log.md`` D22①②（五件套模具复用 verbatim，
权威样版 = ``main_module.py``）；信号键源 = ``output_modules.py``
world_bible 注册项（T7，全 optional 档）；B 信 = T8 StageCode.BIBLE。

三铁律落位（镜像 main_module docstring 契约）：
- ``bible_compile_copy`` 是**唯一 LLM 生产点**：LLM 只产文案
  （overview 一句话 + 各章导语建议），**永不产结构数值**——章节树/
  答案原文全部由确定性代码装配。
- provider 缺席/失败/形状不符 → 确定性骨架兜底（答案原文直投）+
  ledger 披露 ``world_bible_degraded``——零 LLM key 免费线可跑通。
- 六章章节树冻结（顺序即契约）：①世界本体 ②文明与社会 ③历史时间线
  ④地理空间 ⑤力量体系 ⑥设定边界。缺料章**诚实留空**并逐章独立披露
  ``world_bible_empty_chapters``——不 409、不编造（D22 全 optional 档）。
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field

# ── 六章章节树（D22① 冻结，顺序即契约）────────────────────────────────

BIBLE_CHAPTER_HEADINGS: tuple[str, ...] = (
    "世界本体", "文明与社会", "历史时间线", "地理空间", "力量体系", "设定边界",
)

#: 每章 ← 答案信号键映射（与 T7 output_modules world_bible 注册键一致；
#: 缺料章正文留空，诚实不编造）。
_CHAPTER_SIGNALS: dict[str, tuple[str, ...]] = {
    "世界本体": ("世界本体.reality_rule", "世界本体.core_conflict"),
    "文明与社会": ("文明与社会.faction_type",),
    "历史时间线": ("历史时间线.main_plot",),
    "地理空间": ("地理空间.terrain",),
    "力量体系": ("力量体系.cost", "力量体系.acquire"),
    "设定边界": ("设定边界.immutable_core",),
}

_BIBLE_COMPILE_PROMPT = """你是 TRPG 世界观编辑。基于以下世界信号，为世界圣经
输出 JSON 文案（只产文案，不产结构数值）：
{"module_fantasy": "一句话世界核心幻想",
 "sections": {"{章标题}": "该章导语（1-2 句）", ...}}
章标题必须是以下六个之一，不得增删改：
{headings}

世界信号：
{signals}"""


class BibleChapter(BaseModel):
    """六章树节点（镜像 main_module.ModuleDocSection 逐字）。"""
    heading: str
    level: int
    body: str = ""
    children: list["BibleChapter"] = Field(default_factory=list)


class BibleDocument(BaseModel):
    """世界圣经文字版——「产出零加工可用」的直接载体（镜像
    main_module.ModuleDocument :84-95 逐字适配，含溯源字段）。Markdown
    给人，JSON 给机器。"""
    title: str
    overview: str
    chapters: list[BibleChapter]
    graph_code: str
    upstream_graph_code: str
    generated_at: str = ""
    used_stale: bool = False
    # D21⑬/T15：可选 α 版本可见标记（见 a1.draft_version；定稿/存量 = None，
    # 零迁移；α 绝不进持久层）。
    version_label: str | None = None
    upstream_ledger: list[dict[str, Any]] = Field(default_factory=list)
    empty_chapters: list[str] = Field(default_factory=list)


def render_markdown(doc: BibleDocument) -> str:
    """单向序列化：文档 → Markdown（镜像 main_module.render_markdown）。"""
    lines = [f"# {doc.title}", "", f"> {doc.overview}", ""]
    for sec in doc.chapters:
        lines.append(f"{'#' * (sec.level + 1)} {sec.heading}")
        lines.append("")
        if sec.body:
            lines.append(sec.body)
            lines.append("")
    lines.append("---")
    lines.append(f"溯源：{doc.graph_code} ← {doc.upstream_graph_code}")
    return "\n".join(lines)


def _skeleton_chapter_body(heading: str, answers: dict[str, str]) -> str:
    """确定性骨架：映射答案原文直投（镜像 :112-127，不经过任何生成）。"""
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


def bible_compile_copy(provider: Any, answers: dict[str, str]) -> dict | None:
    """bible_compile —— **LLM 单生产点**（镜像 main_module:139-176）。

    只请求文案（overview + 章导语）；任何失败（provider 缺席/网络/
    形状不符）返回 None，由调用方走确定性骨架。永不抛出。
    """
    if provider is None:
        return None
    try:
        signals = "\n".join(
            f"- {k}: {v}" for k, v in sorted(answers.items()) if v.strip()
        )
        messages = [{
            "role": "user",
            "content": _BIBLE_COMPILE_PROMPT.replace(
                "{headings}", "、".join(BIBLE_CHAPTER_HEADINGS),
            ).replace("{signals}", signals or "（无）"),
        }]
        res = provider.chat_json(messages)
        if inspect.isawaitable(res):
            res = asyncio.run(_as_coro(res))
        raw = res
        if not isinstance(raw, dict):
            return None
        fantasy = raw.get("module_fantasy")
        sections = raw.get("sections")
        if not isinstance(fantasy, str) or not fantasy.strip():
            return None
        if not isinstance(sections, dict):
            sections = {}
        clean = {
            h: str(sections[h]).strip()
            for h in BIBLE_CHAPTER_HEADINGS
            if isinstance(sections.get(h), str) and sections[h].strip()
        }
        return {"module_fantasy": fantasy.strip(), "sections": clean}
    except Exception:  # noqa: BLE001 — LLM 永不阻塞主路径（D2-③）
        return None


def compile_world_bible(
    answers: dict[str, str],
    *,
    title: str,
    ip_name: str,
    graph_code: str,
    upstream_graph_code: str,
    provider: Any = None,
    used_stale: bool = False,
    upstream_ledger: list[dict[str, Any]] | None = None,
    issuer: Any = None,
    user_id: str = "",
    ip: int = 0,
) -> tuple[BibleDocument, list[dict[str, Any]]]:
    """确定性装配六章文档；LLM（bible_compile 单点）只叠加文案层
    （镜像 main_module.compile_document :179-234）。

    返回 (document, ledger_entries)；LLM 缺席/失败 → 骨架兜底并披露
    ``world_bible_degraded``；缺料章逐章独立披露
    ``world_bible_empty_chapters``（诚实留空，不 409、不编造）。
    传入 issuer/user_id/ip 时，B 信由 ``issuer.next(stage="B")`` 签发
    （T8 StageCode.BIBLE），覆盖 graph_code 参数。
    """
    if issuer is not None:
        graph_code = issuer.next(user_id, ip, stage="B")

    copy = bible_compile_copy(provider, answers)
    ledger: list[dict[str, Any]] = []
    if copy is None:
        overview = f"{ip_name}：一部可直接查阅的世界圣经（确定性骨架版）"
        degraded = provider is not None
    else:
        overview = copy["module_fantasy"]
        degraded = False

    chapters = [
        BibleChapter(heading=heading, level=2,
                     body=_skeleton_chapter_body(heading, answers))
        for heading in BIBLE_CHAPTER_HEADINGS
    ]
    if copy is not None:
        # LLM 文案只作导语叠加，结构（章树/标题/答案原文）不动——D-A2-4
        for ch in chapters:
            intro = copy["sections"].get(ch.heading)
            if intro:
                ch.body = f"{intro}\n\n{ch.body}" if ch.body else intro

    empty_chapters = [ch.heading for ch in chapters if not ch.body.strip()]
    if empty_chapters:
        from app.domains.creation.a1.warning_ledger import entry as ledger_entry
        ledger.append(dict(ledger_entry(
            "world_bible",
            "world_bible_empty_chapters："
            f"{'、'.join(empty_chapters)} 信号缺失，正文诚实留空（不编造）",
        )))
    if degraded:
        from app.domains.creation.a1.warning_ledger import entry as ledger_entry
        ledger.append(dict(ledger_entry(
            "world_bible",
            "world_bible_degraded：LLM 不可用，世界圣经取确定性骨架"
            "（答案原文直投，免费线可跑通）",
        )))

    doc = BibleDocument(
        title=title,
        overview=overview,
        chapters=chapters,
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        used_stale=used_stale,
        upstream_ledger=list(upstream_ledger or []),
        empty_chapters=empty_chapters,
    )
    return doc, ledger
