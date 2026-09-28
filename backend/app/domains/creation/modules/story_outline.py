"""故事大纲渲染器（M3 产出模块 · D22③）——剧情信号叙事化渲染。

镜像 ``main_module.py`` 五件套模具（D22 施工纪律：渲染器一律复用
主模组模具结构，禁止模具外模式）：
- 冻结章节树：六个剧情信号域各成一节（opening_event/core_dilemma/
  branch_trees/lead_chain/secret_layer/tension_hole，M12 字段定义，
  seed/story_modules.py 实际字段即节），顺序即契约。
- 信号键绑定：``剧情.*`` 键与 T7 注册（output_modules.story_outline
  signal_requirements，全 optional）逐字一致。
- ``compile_copy`` 是本模块唯一 LLM 生产点，**只产文案**（叙事化导语层
  D22①「剧情信号叙事化渲染」），永不产结构数值；任何失败返回 None。
- 装配/降级/序列化/溯源走模具既有模式：骨架答案原文直投、失败降级 +
  ledger 披露 ``story_outline_degraded``、Markdown 单向序列化。
- 编号：O 字母（graph_code_issuer.StageCode.OUTLINE，D22③）。
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field

# ── 六节章节树（M12 剧情字段冻结，顺序即契约）──────────────────────────

STORY_SECTIONS: tuple[str, ...] = (
    "opening_event", "core_dilemma", "branch_trees",
    "lead_chain", "secret_layer", "tension_hole",
)

#: 每节 ← 答案信号键映射（与 T7 注册 signal_requirements 逐字一致）。
SECTION_SIGNALS: dict[str, tuple[str, ...]] = {
    sec: (f"剧情.{sec}",) for sec in STORY_SECTIONS
}

#: 叙事化导语 prompt（D22①：剧情信号叙事化渲染；只产文案不产结构）。
_STORY_OUTLINE_PROMPT = """你是叙事编辑。基于以下剧情信号，为故事大纲输出
JSON 文案（只产文案，不产结构数值），语气须为**叙事化**渲染（把剧情信号
讲成引人入胜的故事引子，而非条目罗列）：
{"lead_in": "整篇故事的叙事化导语（2-3 句）",
 "sections": {"剧情.{信号}": "该节叙事化导语（1-2 句）", ...}}
信号键必须是以下六个之一，不得增删改：
{keys}

剧情信号：
{signals}"""


class StoryOutlineSection(BaseModel):
    """章节树节点（模具 ModuleDocSection 同构）。"""
    heading: str
    level: int
    body: str = ""


class StoryOutlineDocument(BaseModel):
    """故事大纲——「产出零加工可用」载体（模具 ModuleDocument 同构）。"""
    title: str
    lead_in: str
    sections: list[StoryOutlineSection]
    graph_code: str
    upstream_graph_code: str
    generated_at: str = ""
    used_stale: bool = False
    degraded: bool = False
    # D21⑬/T15：可选 α 版本可见标记（见 a1.draft_version；定稿/存量 = None，
    # 零迁移；α 绝不进持久层）。
    version_label: str | None = None
    upstream_ledger: list[dict[str, Any]] = Field(default_factory=list)


def render_markdown(doc: StoryOutlineDocument) -> str:
    """单向序列化：文档 → Markdown（含 O 字母溯源行）。"""
    lines = [f"# {doc.title}", "", f"> {doc.lead_in}", ""]
    for sec in doc.sections:
        lines.append(f"{'#' * (sec.level + 1)} {sec.heading}")
        lines.append("")
        if sec.body:
            lines.append(sec.body)
            lines.append("")
    lines.append("---")
    lines.append(f"溯源：{doc.graph_code} ← {doc.upstream_graph_code}")
    return "\n".join(lines)


def _skeleton_section_body(section: str, answers: dict[str, str]) -> str:
    """确定性骨架：映射答案原文直投（不经过任何生成）。"""
    from app.domains.creation.seed.story_modules import STORY_MODULES

    labels: dict[str, str] = {}
    for m in STORY_MODULES:
        for f in m["fields"]:
            labels[f"{m['id']}.{f['id']}"] = f["label"]

    lines = []
    for key in SECTION_SIGNALS.get(section, ()):
        value = (answers.get(key) or "").strip()
        if value:
            lines.append(f"- {labels.get(key, key)}：{value}")
    return "\n".join(lines)


def _as_coro(awaitable: Any) -> Any:
    """Wrap an awaitable so ``asyncio.run`` receives a coroutine (typing)."""

    async def _run() -> Any:
        return await awaitable

    return _run()


def compile_copy(provider: Any, answers: dict[str, str]) -> dict[str, Any] | None:
    """compile_copy —— 本模块**唯一 LLM 生产点**（模具契约：copy-only）。

    只请求叙事化文案（lead_in + 节导语）；任何失败（provider 缺席/网络/
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
            "content": _STORY_OUTLINE_PROMPT.replace(
                "{keys}", "、".join(STORY_SECTIONS),
            ).replace("{signals}", signals or "（无）"),
        }]
        res = provider.chat_json(messages)
        if inspect.isawaitable(res):
            res = asyncio.run(_as_coro(res))
        raw = res
        if not isinstance(raw, dict):
            return None
        lead_in = raw.get("lead_in")
        sections = raw.get("sections")
        if not isinstance(lead_in, str) or not lead_in.strip():
            return None
        if not isinstance(sections, dict):
            sections = {}
        clean = {
            sec: str(sections[sec]).strip()
            for sec in STORY_SECTIONS
            if isinstance(sections.get(sec), str) and sections[sec].strip()
        }
        return {"lead_in": lead_in.strip(), "sections": clean}
    except Exception:  # noqa: BLE001 — LLM 永不阻塞主路径（模具契约）
        return None


def compile_outline(
    answers: dict[str, str],
    *,
    title: str,
    ip_name: str,
    graph_code: str,
    upstream_graph_code: str,
    provider: Any = None,
    used_stale: bool = False,
    upstream_ledger: list[dict[str, Any]] | None = None,
) -> tuple[StoryOutlineDocument, list[dict[str, Any]]]:
    """确定性装配六节大纲；LLM（compile_copy 单点）只叠加叙事化导语层。

    返回 (document, ledger_entries)；LLM 缺席/失败 → 骨架兜底并披露
    ``story_outline_degraded``（诚实可观测，零 LLM key 免费线可用）。
    """
    copy = compile_copy(provider, answers)
    ledger: list[dict[str, Any]] = []
    if copy is None:
        lead_in = f"{ip_name}：一段可直接开团的剧情大纲（确定性骨架版）"
        degraded = True
    else:
        lead_in = copy["lead_in"]
        degraded = False

    sections = [
        StoryOutlineSection(heading=heading, level=2,
                            body=_skeleton_section_body(heading, answers))
        for heading in STORY_SECTIONS
    ]
    if copy is not None:
        # LLM 叙事化导语只作叠加，结构（节树/标题/答案原文）不动——模具纪律
        for sec in sections:
            intro = copy["sections"].get(sec.heading)
            if intro:
                sec.body = f"{intro}\n\n{sec.body}" if sec.body else intro

    if degraded:
        from app.domains.creation.a1.warning_ledger import entry as ledger_entry
        ledger.append(dict(ledger_entry(
            "finalize",
            "story_outline_degraded：LLM 不可用，故事大纲取确定性骨架"
            "（答案原文直投，免费线可跑通）",
        )))

    doc = StoryOutlineDocument(
        title=title,
        lead_in=lead_in,
        sections=sections,
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        used_stale=used_stale,
        degraded=degraded,
        upstream_ledger=list(upstream_ledger or []),
    )
    return doc, ledger


def issue_outline_code(issuer: Any, user_id: str, ip: int) -> str:
    """O 字母编号签发（graph_code_issuer.StageCode.OUTLINE，D22③）。"""
    code: str = issuer.next(user_id, ip, stage="O")
    return code
