# -*- coding: utf-8 -*-
"""主模组文字版（M3 产出模块 · A2 资产平移）——finalize 八步 + 九节树。

证据：`.sisyphus/evidence/a2-plan-mining-a2-specs.md` §2.5/§6.3；
规格行号：finalize 八步 S1:397-410；九节树 S2:385-403（v0 冻结）；
LLM 失败确定性降级 S1:201/235/413。

三铁律落位（D-A2-4 / DN5 立项）：
- ``module_compile`` 是**唯一 LLM 生产点**（新 LLM 生产方，三铁律
  "单生产单消费"契约评审立项留痕——统一清单见计划 DECISION NEEDED 5）。
  LLM 只产文案（module_fantasy 一句话 + 各节导语建议），**永不产结构
  数值**：章节树/ScopeBoundary/数值全部由确定性代码装配。
- provider 缺席/失败/形状不符 → 确定性骨架兜底（答案原文直投）+
  ledger 披露 ``module_compile_degraded``——零 LLM key 免费线可跑通。
- 九节章节树冻结（S2:400-403）：①模组概述 ②世界背景摘要 ③舞台：区域
  与分区 ④时代与主线 ⑤平行剧情挂点 ⑥势力与冲突 ⑦骰子规则 ⑧角色创建
  指南 ⑨GM 边界须知。D15：ScopeBoundary.max_party_size=6。
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field

# ── 九节章节树（S2:400-403 冻结，顺序即契约）──────────────────────────

NINE_SECTION_HEADINGS: tuple[str, ...] = (
    "模组概述", "世界背景摘要", "舞台：区域与分区", "时代与主线",
    "平行剧情挂点", "势力与冲突", "骰子规则", "角色创建指南", "GM 边界须知",
)

#: 每节 ← 答案信号键映射（确定性装配；缺料节正文留空，诚实不编造）。
_SECTION_SIGNALS: dict[str, tuple[str, ...]] = {
    "模组概述": ("IP定位.name", "IP定位.concept", "剧情.opening_event"),
    "世界背景摘要": ("世界本体.origin", "世界本体.existence",
                     "世界本体.reality_rule"),
    "舞台：区域与分区": ("地理空间.terrain", "地理空间.vertical",
                        "地理空间.special_geo"),
    "时代与主线": ("历史时间线.main_plot", "剧情.core_dilemma"),
    "平行剧情挂点": ("剧情.branch_trees", "剧情.lead_chain",
                    "剧情.secret_layer"),
    "势力与冲突": ("文明与社会.faction_type", "文明与社会.conflict",
                  "文明与社会.core_value", "剧情.tension_hole"),
    "骰子规则": ("骰子设定.probability", "骰子设定.check_mode",
                 "骰子设定.success_check", "骰子设定.cost_mech",
                 "力量体系.cost"),
    "角色创建指南": ("角色.identity", "角色.desire", "角色.key_relations",
                    "角色.arc_direction", "玩法设计DNA.player_role"),
    "GM 边界须知": ("设定边界.immutable_core", "设定边界.ai_fill"),
}

_MODULE_COMPILE_PROMPT = """你是 TRPG 模组编辑。基于以下世界信号，为主模组
输出 JSON 文案（只产文案，不产结构数值）：
{"module_fantasy": "一句话模组核心幻想",
 "sections": {"{节标题}": "该节导语（1-2 句）", ...}}
节标题必须是以下九个之一，不得增删改：
{headings}

世界信号：
{signals}"""


class ScopeBoundary(BaseModel):
    """模组范围契约（S2:270-278 逐字适配；D15：max_party_size=6 胜出）。"""
    allowed_regions: str = ""
    allowed_eras: str = ""
    max_power_level: int | None = None
    core_factions_unmodifiable: bool = True
    max_party_size: int = 6          # D15：S2 缺省值裁决胜出
    content_density: str = "standard"
    source: str = "default"          # default / planning


class ModuleDocSection(BaseModel):
    """九节树节点（S2:385-389 逐字）。"""
    heading: str
    level: int
    body: str = ""
    children: list["ModuleDocSection"] = Field(default_factory=list)


class ModuleDocument(BaseModel):
    """主模组文字版——「产出零加工可用」（D2-①）的直接载体
    （S2:391-403 逐字适配）。Markdown 给人，JSON 给机器。"""
    title: str
    module_fantasy: str
    sections: list[ModuleDocSection]
    scope_boundary: ScopeBoundary
    graph_code: str
    upstream_graph_code: str
    generated_at: str = ""
    used_stale: bool = False
    # D21⑬/T15：可选 α 版本可见标记（会话态草稿期 = "α0.1" 等，见
    # a1.draft_version）。定稿/存量产物为 None（默认缺省，零迁移）——
    # 纯展示标记，α 绝不进持久层（graph_code 仍为整型 vN）。
    version_label: str | None = None
    upstream_ledger: list[dict[str, Any]] = Field(default_factory=list)


def render_markdown(doc: ModuleDocument) -> str:
    """单向序列化：文档 → Markdown（GM 零加工可开团，D2-①/B5）。"""
    lines = [f"# {doc.title}", "", f"> {doc.module_fantasy}", ""]
    for sec in doc.sections:
        lines.append(f"{'#' * (sec.level + 1)} {sec.heading}")
        lines.append("")
        if sec.body:
            lines.append(sec.body)
            lines.append("")
    lines.append("---")
    lines.append(f"溯源：{doc.graph_code} ← {doc.upstream_graph_code}")
    return "\n".join(lines)


def _skeleton_section_body(heading: str, answers: dict[str, str]) -> str:
    """确定性骨架：映射答案原文直投（不经过任何生成）。"""
    from app.domains.creation.seed.a1_question_tree import MODULES
    from app.domains.creation.seed.story_modules import STORY_MODULES

    labels: dict[str, str] = {}
    for m in (*MODULES, *STORY_MODULES):
        for f in m["fields"]:
            labels[f"{m['id']}.{f['id']}"] = f["label"]

    lines = []
    for key in _SECTION_SIGNALS.get(heading, ()):
        value = (answers.get(key) or "").strip()
        if value:
            lines.append(f"- {labels.get(key, key)}：{value}")
    return "\n".join(lines)


def _as_coro(awaitable: Any) -> Any:
    """Wrap an awaitable so ``asyncio.run`` receives a coroutine (typing)."""

    async def _run() -> Any:
        return await awaitable

    return _run()


def module_compile_copy(provider: Any, answers: dict[str, str]) -> dict | None:
    """module_compile —— **LLM 单生产点**（DN5 立项：单生产单消费）。

    只请求文案（module_fantasy + 节导语）；任何失败（provider 缺席/
    网络/形状不符）返回 None，由调用方走确定性骨架。永不抛出。
    """
    if provider is None:
        return None
    try:
        signals = "\n".join(
            f"- {k}: {v}" for k, v in sorted(answers.items()) if v.strip()
        )
        messages = [{
            "role": "user",
            "content": _MODULE_COMPILE_PROMPT.replace(
                "{headings}", "、".join(NINE_SECTION_HEADINGS),
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
            for h in NINE_SECTION_HEADINGS
            if isinstance(sections.get(h), str) and sections[h].strip()
        }
        return {"module_fantasy": fantasy.strip(), "sections": clean}
    except Exception:  # noqa: BLE001 — LLM 永不阻塞主路径（D2-③）
        return None


def compile_document(
    answers: dict[str, str],
    *,
    title: str,
    ip_name: str,
    graph_code: str,
    upstream_graph_code: str,
    provider: Any = None,
    used_stale: bool = False,
    upstream_ledger: list[dict[str, Any]] | None = None,
) -> tuple[ModuleDocument, list[dict[str, Any]]]:
    """确定性装配九节文档；LLM（module_compile 单点）只叠加文案层。

    返回 (document, ledger_entries)；LLM 缺席/失败 → 骨架兜底并披露
    ``module_compile_degraded``（诚实可观测，零 LLM key 免费线可用）。
    """
    copy = module_compile_copy(provider, answers)
    ledger: list[dict[str, Any]] = []
    if copy is None:
        fantasy = f"{ip_name}：一段可直接开团的模组（确定性骨架版）"
        degraded = True
    else:
        fantasy = copy["module_fantasy"]
        degraded = False

    sections = [
        ModuleDocSection(heading=heading, level=2,
                         body=_skeleton_section_body(heading, answers))
        for heading in NINE_SECTION_HEADINGS
    ]
    if copy is not None:
        # LLM 文案只作导语叠加，结构（节树/标题/答案原文）不动——D-A2-4
        for sec in sections:
            intro = copy["sections"].get(sec.heading)
            if intro:
                sec.body = f"{intro}\n\n{sec.body}" if sec.body else intro

    if degraded:
        from app.domains.creation.a1.warning_ledger import entry as ledger_entry
        ledger.append(dict(ledger_entry(
            "finalize",
            "module_compile_degraded：LLM 不可用，主模组文字版取确定性骨架"
            "（答案原文直投，免费线可跑通）",
        )))

    doc = ModuleDocument(
        title=title,
        module_fantasy=fantasy,
        sections=sections,
        scope_boundary=ScopeBoundary(),
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        used_stale=used_stale,
        upstream_ledger=list(upstream_ledger or []),
    )
    return doc, ledger
