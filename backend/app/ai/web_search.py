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

_ZHIPU_TOOLS_URL = "https://open.bigmodel.cn/api/paas/v4/tools"
_MAX_RESULTS = 5
_TIMEOUT_SECONDS = 10.0


def _api_key() -> str | None:
    """Zhipu key from env (project .env is loaded by app config)."""
    return os.environ.get("ZHIPU_API_KEY") or None


async def _search_raw(query: str, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            _ZHIPU_TOOLS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "tool": "web_search",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
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
