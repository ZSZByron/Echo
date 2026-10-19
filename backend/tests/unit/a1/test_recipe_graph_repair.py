"""配方定稿图谱修复红测（施工单 recipe-graph-repair，B1/B2/B3）。

三病灶：
- B1  _build_graph 硬编码世界观 MODULES → 故事配方（剧情/角色）定稿后空图
- B2  graphify 对 AnswerNode 调 len() 崩（finalize_warnings "has no len()"）
- B3  图数据无大陆归属（L1 continent）→ 活地图无从点亮

三类结构：
(a) TestStoryRecipeFinalizeGraph —— TestClient 集成：故事配方定稿 →
    背景树含 剧情/角色 L2 + 15 个 L3 条目 + tree 边 ≥17 + continent 落值
    + finalize_warnings 无 "has no len()"。
(b) TestGraphifyFlatten —— graphify_llm 单元：AnswerNode 摊平进 system
    prompt 且不再抛 "has no len()"。
(c) TestModuleContinent —— module_continent 纯函数：L2 id / 模块 id →
    THREE_TIER_TREE L1 归属；未知返回空串（诚实降级）。
"""
from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.graphify import graphify_llm
from app.domains.creation.a1.guide_engine import AnswerNode
from app.main import app

# 故事配方 15 键答案（剧情 9 + 角色 6；与 M12/M11 字段表逐字对齐）
STORY_ANSWERS: dict[str, Any] = {
    "剧情.core_dilemma": "婚礼当夜接到卧底密令：去就要骗过全家，不去线人今晚会死。",
    "剧情.opening_event": "缉毒警员林澈在妹妹婚礼当夜接到卧底密令。",
    "剧情.tension_hole": "想守住家人的信任，就必须先变成他们最恨的人。",
    "剧情.lead_chain": "追查妹妹失踪前最后接触的三个人。",
    "剧情.secret_layer": "恩师其实就是当年灭门案的目击者。",
    "剧情.branch_trees": "成功→洗清冤屈但失去身份；失败→被迫亡命江湖。",
    "剧情.bound_characters": "推的是林澈自己；拦着他的是养大他的义父——黑警长官。",
    "剧情.arc_direction": "先扬后抑的悲剧循环，结局留一线微光。",
    "剧情.scene_hooks": "雨夜码头（潮湿、霓虹倒影、远处汽笛）。",
    "角色.identity": "表面是婚礼上的普通兄长，实际是待命的卧底警员。",
    "角色.desire": "外显目标是查清失踪真相，深层需要是不再失去家人。",
    "角色.flaw": "习惯把一切扛在自己身上，不肯求助。",
    "角色.key_relations": AnswerNode(
        text="与母亲的关系是他与社会的连接口",
        children=[{"text": "母亲承担了奶粉钱", "children": [], "source": "chat"}],
        source="chat",
    ),
    "角色.arc_direction": "由守护者堕落为孤狼，再于微光中找回自己。",
    "角色.character_visual": "雨夜里穿湿透的西装，袖口藏着警徽。",
}


class FakeProvider:
    """记录 system prompt 后返回空响应（graphify 优雅降级路径）。"""

    def __init__(self) -> None:
        self.last_messages: list[dict[str, str]] | None = None

    async def chat_json(
        self, messages: list[dict[str, str]], **_kwargs: Any
    ) -> dict[str, Any]:
        self.last_messages = messages
        return {}


class TestStoryRecipeFinalizeGraph:
    """B1 集成：故事配方（剧情+角色）定稿后图谱非空且带 continent。"""

    def test_story_recipe_finalize_builds_full_tree(self) -> None:
        client = TestClient(app)

        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u-recipe-test", "custom_idea": "失忆钟表匠"},
        )
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        session = a1_routes._SESSIONS[payload["session_id"]]
        file_id = payload["file_id"]

        # 直改会话：落定故事配方 + 15 键答案（含 1 个 AnswerNode）
        session.recipe_modules = ["剧情", "角色"]
        session.answers.update(STORY_ANSWERS)

        fin = client.post(f"/api/a1/file/{file_id}/finalize")
        assert fin.status_code == 200, fin.text

        # finalize 响应体无 graph 键 → GET /graph 取图
        graph = fin.json()
        if "graph" not in graph:
            graph = client.get(f"/api/a1/file/{file_id}/graph").json()

        nodes = graph["nodes"]
        edges = graph["edges"]

        # level 分布：L2 ≥ 2（剧情/角色），L3 ≥ 15（15 键全落）
        levels = Counter(n["level"] for n in nodes.values())
        assert levels[2] >= 2, f"L2 count={levels[2]}"
        assert levels[3] >= 15, f"L3 count={levels[3]}"

        # tree 边：bg→L2 (2) + L2→L3 (15) ≥ 17
        tree_edges = sum(
            1 for e in edges if e.get("edge_type") == "tree"
        )
        assert tree_edges >= 17, f"tree edges={tree_edges}"

        # B3：L2 节点带 L1 大陆归属（THREE_TIER_TREE 实测 L1 id）
        assert nodes["剧情"]["continent"] == "story_line"
        assert nodes["角色"]["continent"] == "character"

        # B2：finalize_warnings 不再有 AnswerNode len() 崩溃
        fin_resp = client.get(f"/api/a1/file/{file_id}")
        assert fin_resp.status_code == 200
        for w in fin_resp.json().get("finalize_warnings", []):
            assert "has no len()" not in str(w), w


class TestGraphifyFlatten:
    """B2 单元：graphify_llm 入口把非 str 答案摊平为 plain string。"""

    def test_answer_node_flattened_into_prompt(self) -> None:
        provider = FakeProvider()
        session = SimpleNamespace(
            session_id="a1_flatten_test",
            answers={
                "角色.key_relations": STORY_ANSWERS["角色.key_relations"],
                "剧情.core_dilemma": STORY_ANSWERS["剧情.core_dilemma"],
            },
        )

        result = graphify_llm(session, provider)  # type: ignore[arg-type]

        # 摊平文本进 system prompt（AnswerNode → answer_view 纯串）
        assert provider.last_messages is not None
        system = provider.last_messages[0]["content"]
        assert "与母亲的关系是他与社会的连接口" in system
        assert "母亲承担了奶粉钱" in system
        assert "婚礼当夜接到卧底密令" in system

        # 不再抛 "has no len()"（空响应 {} = 合法空 SIR → 成功降级）
        assert "has no len()" not in (result.warning or "")


class TestModuleContinent:
    """B3 单元：module_continent → THREE_TIER_TREE L1 归属。"""

    def test_known_module_ids_map_to_l1(self) -> None:
        from app.domains.creation.a1.live_projection import module_continent

        assert module_continent("剧情") == "story_line"
        assert module_continent("角色") == "character"
        assert module_continent("IP定位") == "ip"

    def test_unknown_module_degrades_to_empty(self) -> None:
        from app.domains.creation.a1.live_projection import module_continent

        assert module_continent("不存在") == ""
