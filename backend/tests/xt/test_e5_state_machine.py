"""E5 极限实验 · 状态机酷刑（用户投票定案 #12）。

打击面 #12 重定稿边断链（C7 三元组精确匹配脆断）：
  confirmed 边匹配键 = from/to/relation 精确比对。深度树 id 是内容锚定的
  （d:{anchor}:{sanitize(title)}），LLM 第二轮输出标题漂移一个字 → 新 id ≠
  旧 id → 用户确认过的边坠落 dead_edges，语义相同的新边以未确认状态复活。

判据：C（契约违反 —— 跨版本 id 稳定性不变量 vs 内容锚定 id 的天然矛盾）。
"""
from __future__ import annotations

import pytest

from app.api import a1_routes
from tests.xt.conftest import full_answers, inject_answers
from tests.xt.helpers import ANCHOR, VALID_REL, FakeProvider, canned_graphify

pytestmark = pytest.mark.xt

FID = f"d:{ANCHOR}:斗气分裂"
TID = f"d:{ANCHOR}:玄煞血脉"
DRIFTED_FID = f"d:{ANCHOR}:斗气裂变"  # 一个字漂移 → 完全不同的 id


def _payload(title_a: str) -> dict:
    return canned_graphify(
        entries=[
            {
                "anchor": ANCHOR,
                "items": [
                    {"title": title_a, "content": "条目甲"},
                    {"title": "玄煞血脉", "content": "条目乙"},
                ],
            }
        ],
        edges=[
            {
                "from": f"d:{ANCHOR}:{title_a}",
                "to": TID,
                "relation": VALID_REL,
                "confidence": "semantic",
            }
        ],
    )


class TestE51RefinalizeEdgeBreak:
    """#12 定稿循环：标题一字漂移 → confirmed 边断链。"""

    @pytest.mark.usefixtures("no_visual_bg")
    def test_confirmed_edge_snaps_on_title_drift(self, started, monkeypatch):
        client, payload = started
        inject_answers(payload["session_id"], full_answers())

        # ---- 第一轮定稿：两个条目 + 一条边 ----
        fake = FakeProvider(_payload("斗气分裂"))
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)
        r1 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert r1.status_code == 200
        code1 = r1.json()["graph_code"]
        rec = a1_routes._FILES[payload["file_id"]]
        assert FID in rec["graph_json"]["nodes"]
        assert TID in rec["graph_json"]["nodes"]

        # 用户确认这条边（注入 confirmed 快照 = /edge/confirm 的持久化形态）
        edge_key = f"{FID}/{TID}/{VALID_REL}"
        rec["confirmed_edges"] = {
            edge_key: {
                "from_node_id": FID,
                "to_node_id": TID,
                "relation": VALID_REL,
            }
        }

        # ---- 第二轮定稿：LLM 标题漂移一个字 ----
        fake.payload = _payload("斗气裂变")
        r2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert r2.status_code == 200
        code2 = r2.json()["graph_code"]
        assert code2 != code1  # 同实例再定稿，版本 +1（或新实例）

        rec = a1_routes._FILES[payload["file_id"]]
        graph = rec["graph_json"]

        # BUG(#12)/C7: 旧 confirmed 边的端点从图中消失 → 坠入死区（有记录，契约如此）
        assert any(
            de.get("key") == edge_key and de.get("reason") == "endpoint_missing"
            for de in rec["dead_edges"]
        )
        # 旧节点消失，新漂移节点出现
        assert FID not in graph["nodes"]
        assert DRIFTED_FID in graph["nodes"]

        # 语义相同的新边以"未确认"状态复活 —— 用户必须重新确认
        new_edge = next(
            e
            for e in graph["edges"]
            if e["from_node_id"] == DRIFTED_FID and e["to_node_id"] == TID
        )
        assert new_edge["confirmed"] is False  # 确认状态不跨版本迁移
