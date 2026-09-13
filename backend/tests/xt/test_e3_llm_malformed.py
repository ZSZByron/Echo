"""E3 极限实验 · LLM 输出畸形（用户投票定案头号目标 #7）。

打击面 #7 标题碰撞（32 字同前缀双胞胎）：
  层1  sanitize_title 截断 32 字 → 两个不同条目铸出同一深度树 id
  层2  dedupe_items 丢第二条（有警告 —— 非静默）
  层3  引用第二条的边：LLM 写的是全长标题 id，节点表里只有 32 字截断 id
       → graphify 校验层按"幻觉端点"丢边 —— 警告链曾断裂（只进
       llm_result.warning 且 success=True 时蒸发）
       → J3 已修复（2026-09-11）：警告落结构化 ledger（source=graphify），
         层3 断言已翻转为期望行为；id 同前缀碰撞本体归 J2 规范化层

判据：B+C（条目层丢失有记录；边层丢失 = 警告进 ledger，不再静默）。
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

        # J3 fixed(#7 警告链断裂)：边层丢失警告现在进结构化 ledger
        # （source=graphify），不再随 success=True 蒸发；也不混入旧通道
        # （assemble/finalize 语义边界保持——graphify 层归 graphify source）
        led = rec["warnings"]
        dropped = next(
            e for e in led
            if e["source"] == "graphify" and "引用了不存在的节点" in e["detail"]
        )
        assert dropped["level"] == "warn"
        assert dropped["count"] == 1
        assert not any(
            "引用了不存在的节点" in w for w in rec.get("assemble_warnings", [])
        )
        assert not any(
            "引用了不存在的节点" in w for w in rec.get("finalize_warnings", [])
        )
        # 边死区仍没有它（丢弃发生在 graphify 校验层，早于 _merge_llm_edges
        # 的端点核验——ledger 是它唯一的持久化痕迹）
        assert rec["dead_edges"] == []
        # 图里也确实没有这条边
        assert not any(
            e["from_node_id"].endswith(TWIN_T2) or e["to_node_id"].endswith(TWIN_T1)
            for e in graph["edges"]
        )
