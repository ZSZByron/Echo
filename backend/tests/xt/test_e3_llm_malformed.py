"""E3 极限实验 · LLM 输出畸形（用户投票定案头号目标 #7）。

打击面 #7 标题碰撞（32 字同前缀双胞胎）：
  层1  sanitize_title 截断 32 字 → 两个不同条目铸出同一深度树 id
  层2  dedupe_items 丢第二条（有警告 —— 非静默）
  层3  引用第二条的边：LLM 写的是全长标题 id，节点表里只有 32 字截断 id
       → graphify 校验层按"幻觉端点"丢边 —— 而 graphify 层警告不进
       assemble_warnings/finalize_warnings —— 警告链断裂，边蒸发于无痕

判据：B+C（条目层丢失有记录；边层丢失 = 警告本身被静默丢弃）。
"""
from __future__ import annotations

import pytest

from app.api import a1_routes
from app.domains.creation.a1.graphify import (
    EntryItem,
    dedupe_items,
    sanitize_title,
)
from tests.xt.conftest import full_answers, inject_answers
from tests.xt.helpers import (
    ANCHOR,
    PREFIX32,
    TWIN_T1,
    TWIN_T2,
    VALID_REL,
    FakeProvider,
    canned_graphify,
)

pytestmark = pytest.mark.xt


class TestE31TwinTitleCollision:
    """#7 同前缀标题对撞（全场性价比最高的一发）。"""

    def test_layer1_sanitize_collision(self):
        assert TWIN_T1 != TWIN_T2
        # 病理确认：34 字标题被截到 32 字 → 不同条目同 id
        assert sanitize_title(TWIN_T1) == sanitize_title(TWIN_T2) == PREFIX32

    def test_layer2_dedupe_drops_second_with_warning(self):
        kept, dupes = dedupe_items(
            [
                EntryItem(title=TWIN_T1, content="甲条目"),
                EntryItem(title=TWIN_T2, content="乙条目"),
            ]
        )
        assert [i.title for i in kept] == [TWIN_T1]  # 保留首条
        assert dupes == [TWIN_T2]  # 重复被报告 → 函数层非静默

    @pytest.mark.usefixtures("no_visual_bg")
    def test_layer3_route_double_loss_and_broken_warning_chain(
        self, started, monkeypatch
    ):
        client, payload = started
        inject_answers(payload["session_id"], full_answers())

        twin_edge = {
            "from": f"d:{ANCHOR}:{TWIN_T2}",  # LLM 用全长标题引用第二条
            "to": f"d:{ANCHOR}:{TWIN_T1}",
            "relation": VALID_REL,
            "confidence": "semantic",
        }
        fake = FakeProvider(
            canned_graphify(
                entries=[
                    {
                        "anchor": ANCHOR,
                        "items": [
                            {"title": TWIN_T1, "content": "甲"},
                            {"title": TWIN_T2, "content": "乙"},
                        ],
                    }
                ],
                edges=[twin_edge],
            )
        )
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert resp.status_code == 200

        rec = a1_routes._FILES[payload["file_id"]]
        graph = rec["graph_json"]

        # 条目层：只有 32 字截断 id 的孪生节点挂载成功（第二条被去重）
        assert f"d:{ANCHOR}:{PREFIX32}" in graph["nodes"]
        # 全长 T2 id 不存在于图中
        assert f"d:{ANCHOR}:{TWIN_T2}" not in graph["nodes"]

        # 条目层丢失有记录（assemble_warnings 有"重复条目去重"）→ 非静默 ✓
        assert any("重复条目去重" in w for w in rec["assemble_warnings"])

        # BUG(#7): 边层丢失发生在 graphify 校验层（"引用了不存在的节点"），
        # 该警告只写进 llm_result.warning —— 而 finalize 只在 success=False 时
        # 才把 warning 并入 finalize_warnings，_assemble_depth_tree 的
        # assemble_warnings 也不含它 → 这条边从图里蒸发，且没有任何持久化痕迹：
        assert rec["dead_edges"] == []  # 边死区没有它（根本没到 _merge_llm_edges）
        assert not any(
            "引用了不存在的节点" in w for w in rec.get("assemble_warnings", [])
        )
        assert not any(
            "引用了不存在的节点" in w for w in rec.get("finalize_warnings", [])
        )
        # 图里也确实没有这条边
        assert not any(
            e["from_node_id"].endswith(TWIN_T2) or e["to_node_id"].endswith(TWIN_T1)
            for e in graph["edges"]
        )
