"""Web search client — Zhipu web_search tool.

Used by the A1 interviewer: when the user cannot understand a concept,
we search the web for reference material and inject it into the LLM
prompt so the guidance reply can explain and inspire.

Degradation contract:
    Any failure (missing key, HTTP error, empty result) returns "".
    Callers must treat "" as "no reference material" and proceed
    with the normal guidance flow — never crash the interview session.
"""
from __future__ import annotations

import asyncio
import os

import httpx

# 2026-10-09 修复：旧 /tools 端点契约已死（无 model 字段必返 1211「模型不存在」），
# 切换至官方现行 Web Search API。响应的 search_result 结构与旧端点一致。
_ZHIPU_SEARCH_URL = "https://open.bigmodel.cn/api/paas/v4/web_search"
_MAX_RESULTS = 5
_TIMEOUT_SECONDS = 10.0


def _api_key() -> str | None:
    """Zhipu key from env (project .env is loaded by app config)."""
    return os.environ.get("ZHIPU_API_KEY") or None


async def _search_raw(query: str, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            _ZHIPU_SEARCH_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "search_query": query,
                "search_engine": "search_std",
                "search_intent": False,
                "count": _MAX_RESULTS,
            },
        )
        resp.raise_for_status()
        return resp.json().get("search_result") or []


def _format_results(results: list[dict]) -> str:
    lines = []
    for item in results[:_MAX_RESULTS]:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        if content:
            lines.append(f"- {title}：{content}" if title else f"- {content}")
    return "\n".join(lines)


async def web_search(query: str) -> str:
    """Search the web and return a digest; '' on any failure."""
    key = _api_key()
    if not key or not query.strip():
        return ""
    try:
        results = await _search_raw(query.strip(), key)
    except Exception:  # noqa: BLE001 — degrade, never crash the session
        return ""
    return _format_results(results)


def search_sync(query: str) -> str:
    """Blocking wrapper for code paths that run inside asyncio.run()."""
    try:
        return asyncio.run(web_search(query))
    except Exception:  # noqa: BLE001
        return ""
