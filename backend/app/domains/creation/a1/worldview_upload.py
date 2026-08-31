"""A1 worldview upload pipeline — upload → format check → copyright
screening → module parsing (prefill) per design doc
docs/plans/2026-08-25-a1-worldview-upload-design.md.

Stages (LLM calls via provider.chat_json, mirroring RealLLMInterviewer's
asyncio.run convention):
    1. extract_entities  — proper nouns for copyright comparison
    2. check_copyright   — knowledge-based screening against published IP
    3. parse_modules     — fill the 10-module question tree (single source
                           of truth: a1_question_tree.MODULES)
    4. convert_text      — rewrite matched proper nouns (user opted in)

Copyright screening is an isolated stage returning {risk_level, matches}
so a future web-search backend (Tavily/Serp) can replace the LLM
implementation without touching the pipeline.
"""
from __future__ import annotations

import asyncio
import unicodedata
from typing import Any

from app.ai.provider import LLMProvider
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
)

# MVP limits (design doc): reject tiny texts, truncate huge ones.
MIN_CONTENT_CHARS = 200
MAX_CONTENT_CHARS = 20000
MAX_PROPER_NOUN_ITEMS = 10

RISK_HIGH = "high"
RISK_LOW = "low"


# ---------------------------------------------------------------------------
# Stage 0 — format validation (pure rules, no LLM)
# ---------------------------------------------------------------------------

def validate_text(filename: str, content: str) -> dict[str, Any]:
    """Rule-based gate: length, text-ness, filename presence."""
    if not filename or not filename.strip():
        return {"ok": False, "reason": "文件名为空"}
    if not content or not content.strip():
        return {"ok": False, "reason": "文档内容为空"}
    if len(content.strip()) < MIN_CONTENT_CHARS:
        return {
            "ok": False,
            "reason": f"文档太短（{len(content.strip())} 字符），至少需要 {MIN_CONTENT_CHARS} 字符",
        }
    # Binary masquerade check: ratio of control / non-printable chars.
    control = sum(
        1
        for ch in content
        if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t"
    )
    if control / len(content) > 0.1:
        return {"ok": False, "reason": "文件包含大量二进制字符，请上传纯文本文档"}
    return {"ok": True, "reason": ""}


def _truncate(content: str) -> tuple[str, bool]:
    """Cap content at MAX_CONTENT_CHARS; report whether truncation happened."""
    if len(content) <= MAX_CONTENT_CHARS:
        return content, False
    return content[:MAX_CONTENT_CHARS], True


async def _chat_json(provider: LLMProvider, system: str, user: str) -> dict[str, Any]:
    raw = await provider.chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    if not isinstance(raw, dict):
        raise ValueError(f"LLM 返回了非对象 JSON: {type(raw).__name__}")
    return raw


# ---------------------------------------------------------------------------
# Stage 1 — entity extraction
# ---------------------------------------------------------------------------

async def extract_entities(provider: LLMProvider, text: str) -> dict[str, Any]:
    """LLM call #1: proper nouns used for copyright comparison."""
    snippet, truncated = _truncate(text)
    system = (
        "你是版权风险分析助手。从用户提交的世界观文本中提取专有名词，"
        "用于后续版权比对。只提取多次出现、或对世界观有结构作用的内容，"
        "不列一次性提及的次要名词。每类最多 "
        f"{MAX_PROPER_NOUN_ITEMS} 项。"
        '输出 JSON：{"characters": [...], "power_systems": [...], '
        '"world_keywords": [...], "suspected_works": [...]}。'
        "suspected_works 是文中自述的作品名/系列名，没有则为空数组。"
    )
    raw = await _chat_json(provider, system, snippet)
    entities: dict[str, Any] = {
        "characters": raw.get("characters") or [],
        "power_systems": raw.get("power_systems") or [],
        "world_keywords": raw.get("world_keywords") or [],
        "suspected_works": raw.get("suspected_works") or [],
    }
    for key in ("characters", "power_systems", "world_keywords", "suspected_works"):
        raw_list = entities[key]
        if isinstance(raw_list, str) or not isinstance(raw_list, (list, tuple)):
            items: list[str] = []  # tolerate scalar/garbage shapes
        else:
            items = [str(x).strip() for x in raw_list if x]
        # Dedup (preserve order) then cap.
        entities[key] = list(dict.fromkeys(items))[:MAX_PROPER_NOUN_ITEMS]
    entities["truncated"] = truncated
    return entities


# ---------------------------------------------------------------------------
# Stage 2 — copyright screening (replaceable stage)
# ---------------------------------------------------------------------------

async def check_copyright(
    provider: LLMProvider, entities: dict[str, Any]
) -> dict[str, Any]:
    """LLM call #2: knowledge-based screening. Only high-confidence
    matches are flagged — prefer false negatives over pestering original
    authors with false positives."""
    system = (
        "你是IP版权合规审核员。基于你的知识，判断以下专有名词是否属于"
        "已发布的小说/游戏/影视作品（含网络小说）。"
        "只标记你高度确定命中的知名已发表作品；不确定或冷门的归为 low 并留空 matches，"
        "宁可漏报不可误报。"
        '输出 JSON：{"risk_level": "high"|"low", '
        '"matches": [{"term": "...", "work": "...", "evidence": "..."}]}。'
    )
    user = (
        f"主要角色：{entities.get('characters') or []}\n"
        f"力量体系：{entities.get('power_systems') or []}\n"
        f"世界观关键词：{entities.get('world_keywords') or []}\n"
        f"疑似作品名：{entities.get('suspected_works') or []}"
    )
    raw = await _chat_json(provider, system, user)
    matches = raw.get("matches") or []
    core_terms = set(entities.get("characters") or []) | set(
        entities.get("power_systems") or []
    )
    valid = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        term = str(m.get("term") or "").strip()
        if not term:
            continue
        valid.append({
            "term": term,
            "work": str(m.get("work") or ""),
            "evidence": str(m.get("evidence") or ""),
        })
    # High risk only when a hit lands on a main character or core power system.
    risk = (
        RISK_HIGH
        if raw.get("risk_level") == RISK_HIGH
        or any(m["term"] in core_terms for m in valid)
        else RISK_LOW
    )
    return {"risk_level": risk, "matches": valid}


# ---------------------------------------------------------------------------
# Stage 3 — module parsing (single source of truth: MODULES)
# ---------------------------------------------------------------------------

def _schema_catalog() -> str:
    lines = []
    for module in MODULES:
        for sf in module["fields"]:
            lines.append(
                f"{module['id']}.{sf['id']} | {sf['question']} | 示例: {sf.get('example', '')}"
            )
    return "\n".join(lines)


async def parse_modules(provider: LLMProvider, text: str) -> dict[str, Any]:
    """LLM call #3: fill the 10-module question tree. The schema is
    programmatically derived from a1_question_tree.MODULES so it can
    never drift from the locked module order. Fields without textual
    evidence must be omitted, never fabricated."""
    snippet, truncated = _truncate(text)
    system = (
        "你是世界观结构化专家。将用户文本按模块 schema 填充。\n"
        f"schema（模块id.字段id | 问题 | 示例）：\n{_schema_catalog()}\n"
        '输出 JSON：{"answers": {"模块id.字段id": "一句话答案", ...}, '
        '"innovations": [{"field": "...", "suggestion": "..."}]}。\n'
        "铁律：只使用 schema 中存在的 key；文档中没有依据的字段直接缺省该 key，"
        "禁止编造。innovations 是超出 10 模块标准框架的原创点（0~5 条），"
        "field 写创新点名，suggestion 写具体内容。"
    )
    raw = await _chat_json(provider, system, snippet)
    raw_answers = raw.get("answers") or {}
    valid_keys = set(all_subfield_keys())
    answers: dict[str, str] = {}
    if isinstance(raw_answers, dict):
        for key, value in raw_answers.items():
            key = str(key)
            if key in valid_keys and value and str(value).strip():
                answers[key] = str(value).strip()
    innovations: list[dict[str, str]] = []
    for item in raw.get("innovations") or []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "").strip()
        suggestion = str(item.get("suggestion") or "").strip()
        if field and suggestion:
            innovations.append({"field": field, "suggestion": suggestion})
        if len(innovations) >= 5:
            break
    return {"answers": answers, "innovations": innovations, "truncated": truncated}


# ---------------------------------------------------------------------------
# Stage 4 — transformative rewrite (user opted in via /upload/convert)
# ---------------------------------------------------------------------------

async def convert_text(
    provider: LLMProvider, text: str, matches: list[dict[str, str]]
) -> str:
    """LLM call #4: rewrite preserving structure/causality while replacing
    matched proper nouns with style-consistent original names."""
    hit_lines = "\n".join(
        f"- {m['term']}（命中作品：{m.get('work', '未知')}）" for m in matches
    )
    system = (
        "你是合规改写师。保留用户文本的世界观结构、剧情逻辑与体验设计，"
        "替换所有命中的专有名词（角色名/体系名/地名）为风格一致的原创名，"
        "并改写与原作直接关联的独特设定表述。\n"
        "禁止改变事件因果关系；禁止增删章节。\n"
        "输出 JSON：{\"converted\": \"净化后的全文\"}。"
    )
    user = f"命中列表：\n{hit_lines}\n\n原文：\n{text}"
    raw = await _chat_json(provider, system, user)
    converted = str(raw.get("converted") or "").strip()
    if not converted:
        raise ValueError("LLM 转换结果为空")
    return converted


def run(coro: Any) -> Any:
    """Run an async pipeline stage from sync route handlers (TestClient
    has no running loop; matches RealLLMInterviewer's asyncio.run use)."""
    return asyncio.run(coro)
