"""D24 T1: web_search 契约测试——降级契约 + 新端点形状（锁定 2026-10-09 修复）。"""
import httpx

from app.ai import web_search


class _StubResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


class _StubClient:
    """捕获 payload 并回放 stub 响应。"""
    resp = None
    captured = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        type(self).captured = {"url": url, "headers": headers, "json": json}
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


def _run(monkeypatch, key="k" * 49, resp=None, exc=None):
    monkeypatch.setenv("ZHIPU_API_KEY", key)
    if exc is not None:
        _StubClient.resp = exc
    else:
        _StubClient.resp = resp
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kw: _StubClient())
    return web_search.search_sync("精神病院 腕带 作用")


def test_missing_key_returns_empty(monkeypatch):
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    assert web_search.search_sync("任何") == ""


def test_http_error_degrades_to_empty(monkeypatch):
    assert _run(monkeypatch, exc=httpx.ConnectError("boom")) == ""


def test_empty_results_return_empty(monkeypatch):
    assert _run(monkeypatch, resp=_StubResp({"search_result": []})) == ""


def test_uses_new_endpoint_and_payload(monkeypatch):
    digest = _run(monkeypatch, resp=_StubResp(
        {"search_result": [{"title": "腕带", "content": "身份识别"}]}))
    cap = _StubClient.captured
    assert cap["url"] == "https://open.bigmodel.cn/api/paas/v4/web_search"
    assert cap["json"]["search_query"] == "精神病院 腕带 作用"
    assert cap["json"]["search_engine"] == "search_std"
    assert cap["headers"]["Authorization"].startswith("Bearer ")
    assert digest == "- 腕带：身份识别"


def test_digest_caps_at_five(monkeypatch):
    items = [{"title": f"t{i}", "content": f"c{i}"} for i in range(7)]
    digest = _run(monkeypatch, resp=_StubResp({"search_result": items}))
    assert len(digest.splitlines()) == 5
