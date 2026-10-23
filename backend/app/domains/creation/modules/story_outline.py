"""故事大纲渲染器（M3 产出模块 · D22③）——真写作大纲（方案 B）。

镜像 ``main_module.py`` 五件套模具（D22 施工纪律：渲染器一律复用
主模组模具结构，禁止模具外模式）：
- 信号键绑定：``剧情.*`` 键与 T7 注册（output_modules.story_outline
  signal_requirements，全 optional）逐字一致（STORY_SECTIONS/
  SECTION_SIGNALS/_skeleton_section_body 同时承担 T7 注册绑定契约）。
- ``compile_outline_llm`` 是本模块唯一 LLM 生产点：产出**结构化写作
  大纲**（一句话梗概/主题人物/三幕节拍/章节分解/伏笔埋收/支线交点），
  输入不限剧情.*（世界观/角色素材一并合成）；任何失败（provider 缺席/
  网络/形状不符）返回 None。
- 装配/降级/序列化/溯源走模具既有模式：LLM 成功装配六形写作大纲节树；
  失败降级为六节骨架（答案原文直投）+ ledger 披露
  ``story_outline_degraded``、Markdown 单向序列化。
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

#: 真写作大纲 prompt（方案 B：LLM 只做素材合成，结构由确定性代码装配；
#: 诚实纪律写死——素材无依据的节返回空数组，禁止编造人物设定）。
_STORY_OUTLINE_PROMPT = """你是故事结构编辑。基于以下全部访谈素材（剧情/世界观/
角色等），合成一份**真写作大纲**，输出 JSON（字段名逐字一致）：
{"lead_in": "整篇大纲引语（1-2 句）",
 "logline": "一句话梗概：当[引发事件]，[主角]必须[目标]，否则[代价]",
 "theme": "主题之问（1 句，素材无依据可空串）",
 "protagonist": "主角想要X/需要Y/错误信念Z（1-2 句）",
 "antagonist": "主要对抗力量及其目标（1 句，可空串）",
 "acts": [{"name": "第一幕·开端", "summary": "本幕概要（1-2 句）",
           "beats": ["节拍1", ...]}, ...（主线三幕结构：开端-对抗-结局，
           至少 1 幕）],
 "chapters": [{"title": "第1章 …", "goal": "目标", "obstacle": "阻碍",
               "outcome": "结果", "cost": "代价", "hook": "章尾钩（可空）"}...],
 "foreshadowing": [{"plant": "伏笔", "payoff": "回收点",
                    "weight": "高|中|低"}...],
 "subplots": [{"name": "支线名", "tie": "与主线交点"}...]}
（chapters 即章节分解：每章按目标-阻碍-结果-代价-钩展开。）

诚实纪律：只用用户素材合成；素材无依据的节（如伏笔/支线/章节）必须返回
空数组，禁止编造人物设定与情节事实。

访谈素材：
{signals}"""

#: 帽值常量（防 LLM 灌水；超帽静默截断，不算失败）。
MAX_CHAPTERS = 24
MAX_BEATS_PER_ACT = 6
MAX_FORESHADOWING = 12
MAX_SUBPLOTS = 6


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


def _s(value: Any) -> str:
    """非空字符串 → 去空格；否则空串（装配层防脏，不吞错）。"""
    return value.strip() if isinstance(value, str) else ""


def compile_outline_llm(
    provider: Any, answers: dict[str, str],
) -> dict[str, Any] | None:
    """compile_outline_llm —— 本模块**唯一 LLM 生产点**（真写作大纲）。

    全部 answers（不限剧情.*）喂给 LLM 合成结构化写作大纲；任一硬伤
    （provider 缺席/网络/形状不符：lead_in 或 logline 非空串缺失、
    acts 非列表或空项、可省列表元素非 dict）整体判失败返回 None，
    由调用方走确定性骨架。永不抛出。超帽静默截断（不算失败）。
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
                "{signals}", signals or "（无）",
            ),
        }]
        res = provider.chat_json(messages)
        if inspect.isawaitable(res):
            res = asyncio.run(_as_coro(res))
        raw = res
        if not isinstance(raw, dict):
            return None
        # 硬校验：任一硬伤 → 整体判失败（走降级，不部分采信）
        lead_in = raw.get("lead_in")
        logline = raw.get("logline")
        acts = raw.get("acts")
        if not isinstance(lead_in, str) or not lead_in.strip():
            return None
        if not isinstance(logline, str) or not logline.strip():
            return None
        if not isinstance(acts, list) or not acts:
            return None
        for act in acts:
            if not isinstance(act, dict) or not _s(act.get("name")):
                return None
        for key in ("chapters", "foreshadowing", "subplots"):
            val = raw.get(key)
            if not isinstance(val, list):
                return None
            if not all(isinstance(item, dict) for item in val):
                return None
        return {
            "lead_in": lead_in.strip(),
            "logline": logline.strip(),
            "theme": _s(raw.get("theme")),
            "protagonist": _s(raw.get("protagonist")),
            "antagonist": _s(raw.get("antagonist")),
            "acts": [
                {
                    "name": _s(act.get("name")),
                    "summary": _s(act.get("summary")),
                    "beats": [
                        _s(b) for b in
                        (act.get("beats") or [])[:MAX_BEATS_PER_ACT]
                        if _s(b)
                    ],
                }
                for act in acts
            ],
            "chapters": raw.get("chapters")[:MAX_CHAPTERS],
            "foreshadowing": raw.get("foreshadowing")[:MAX_FORESHADOWING],
            "subplots": raw.get("subplots")[:MAX_SUBPLOTS],
        }
    except Exception:  # noqa: BLE001 — LLM 永不阻塞主路径（模具契约）
        return None


def _outline_sections(outline: dict[str, Any]) -> list[StoryOutlineSection]:
    """确定性装配六形写作大纲节树（LLM 只供素材，结构全部代码组装）。"""
    sections: list[StoryOutlineSection] = [
        StoryOutlineSection(heading="一句话梗概", level=2,
                            body=outline["logline"]),
    ]
    # 主题与人物：标签式三行，空字段省略行
    profile_lines = []
    for label, key in (("主题", "theme"), ("主角", "protagonist"),
                       ("反抗力量", "antagonist")):
        if outline[key]:
            profile_lines.append(f"- {label}：{outline[key]}")
    if profile_lines:
        sections.append(StoryOutlineSection(
            heading="主题与人物", level=2, body="\n".join(profile_lines),
        ))
    # 主线三幕节拍：每幕 level3 子节（summary 段 + beats 列表）
    if outline["acts"]:
        sections.append(StoryOutlineSection(
            heading="主线三幕节拍", level=2, body="",
        ))
        for act in outline["acts"]:
            body_parts = []
            if act["summary"]:
                body_parts.append(act["summary"])
            body_parts.extend(f"- {b}" for b in act["beats"])
            sections.append(StoryOutlineSection(
                heading=act["name"], level=3, body="\n".join(body_parts),
            ))
    # 章节分解：列表行（前端轻量渲染器不支持表格，列表最兼容）
    if outline["chapters"]:
        ch_lines = []
        for n, ch in enumerate(outline["chapters"], start=1):
            line = (f"- 第{n}章 {_s(ch.get('title'))}："
                    f"目标「{_s(ch.get('goal'))}」→ "
                    f"阻碍「{_s(ch.get('obstacle'))}」→ "
                    f"结果「{_s(ch.get('outcome'))}」（代价：{_s(ch.get('cost'))}")
            hook = _s(ch.get("hook"))
            if hook:
                line += f"；钩：{hook}"
            ch_lines.append(line + "）")
        sections.append(StoryOutlineSection(
            heading="章节分解", level=2, body="\n".join(ch_lines),
        ))
    # 伏笔与回收（空则整节省略）
    if outline["foreshadowing"]:
        fs_lines = [
            f"- {_s(f.get('plant'))} → {_s(f.get('payoff'))}"
            f"（重要度：{_s(f.get('weight'))}）"
            for f in outline["foreshadowing"]
        ]
        sections.append(StoryOutlineSection(
            heading="伏笔与回收", level=2, body="\n".join(fs_lines),
        ))
    # 支线与交点（空则整节省略）
    if outline["subplots"]:
        sp_lines = [
            f"- {_s(s.get('name'))}——{_s(s.get('tie'))}"
            for s in outline["subplots"]
        ]
        sections.append(StoryOutlineSection(
            heading="支线与交点", level=2, body="\n".join(sp_lines),
        ))
    return sections


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
    """确定性装配真写作大纲；LLM（compile_outline_llm 单点）供结构素材。

    返回 (document, ledger_entries)；LLM 缺席/失败/形状不符 → 六节骨架
    兜底并披露 ``story_outline_degraded``（诚实可观测，零 LLM key
    免费线可用）。
    """
    outline = compile_outline_llm(provider, answers)
    ledger: list[dict[str, Any]] = []
    if outline is None:
        lead_in = f"{ip_name}：一段可直接开团的剧情大纲（确定性骨架版）"
        degraded = True
    else:
        lead_in = outline["lead_in"]
        degraded = False

    if degraded:
        sections = [
            StoryOutlineSection(heading=heading, level=2,
                                body=_skeleton_section_body(heading, answers))
            for heading in STORY_SECTIONS
        ]
    else:
        sections = _outline_sections(outline)

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
