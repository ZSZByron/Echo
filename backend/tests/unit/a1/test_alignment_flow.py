"""对齐四动作（alignment_flow，T16，D21⑬）契约测试。

铁律（D21⑬）：LLM 只提议；应用 = 确定性代码执行；
LLM 绝不直写图谱/会话状态——测试断言钉死。

四动作闭集（逐字，不允许添加或修改）：关联 / 去重 / 矛盾 / 更新。
确定性校验器 = 提案池唯一闸门（单点过滤）。

TDD RED：实现前本文件全部失败。
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.alignment_flow import (
    ALIGN_ACTIONS,
    AlignmentProposer,
    build_stale_warning,
    install_proposals,
    render_proposal,
    resolve_alignment,
)
from app.domains.creation.shared import stale_marker


# ── Fixtures ────────────────────────────────────────────────────────────────


def make_graph() -> dict[str, Any]:
    return {
        "nodes": {
            "世界本体": {"description": "意志扭曲物质", "title": ""},
            "d:世界本体.sub:essence:灵潮潮汐": {"description": "灵潮的周期涨落", "title": "灵潮潮汐"},
        },
        "edges": [
            {"key": "世界本体->世界本体", "source": "世界本体", "target": "世界本体",
             "label": "自洽"},
        ],
    }


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class SyncStubProvider:
    """chat_json returns a canned dict synchronously（inference_pack 先例）."""

    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.calls = 0

    def chat_json(self, messages: Any) -> Any:  # noqa: ARG002
        self.calls += 1
        return self._payload


def _payload_all_four() -> dict[str, Any]:
    """四动作各一条合法提案 + 两条非法提案（校验器必须丢弃）。"""
    return {
        "proposals": [
            {"action": "link", "target": "世界本体",
             "content": "你提到的「灵潮」和已有记录里的世界根基设定是相关的",
             "quote": "灵潮是意志的海洋化"},
            {"action": "dedupe", "target": "d:世界本体.sub:essence:灵潮潮汐",
             "content": "你说的灵潮涨落其实和已记录的「灵潮潮汐」是一回事，不用重复记",
             "quote": "灵潮每隔一段时间涨落"},
            {"action": "contradict", "target": "世界本体",
             "content": "你刚说的和之前记录的根基设定有冲突，想保留哪个？",
             "quote": "意志其实无法改变物质"},
            {"action": "update", "target": "d:世界本体.sub:essence:灵潮潮汐",
             "content": "按你最新的说法，之前那条「灵潮潮汐」记录应该改一改",
             "quote": "灵潮其实是十二年的周期"},
            # 非法：动作外
            {"action": "delete", "target": "世界本体",
             "content": "删掉它", "quote": "删掉"},
            # 非法：目标不存在
            {"action": "update", "target": "不存在的节点",
             "content": "改一条不存在的记录", "quote": "改"},
        ],
    }


# ── 四动作 契约（提议→校验→确认→应用） ──────────────────────────────────────


class TestFourActionContract:
    @pytest.mark.parametrize("action", list(ALIGN_ACTIONS))
    def test_propose_validate_accept_apply(self, action: str):
        graph = make_graph()
        session = make_session()
        provider = SyncStubProvider(_payload_all_four())

        pack = AlignmentProposer(provider).propose(graph, "灵潮是十二年的周期")

        assert provider.calls == 1  # 单次调用（inference_pack 先例）
        # 动作闭集校验：非法（delete / 目标不存在）被确定性过滤
        kept = {p.action for p in pack.proposals}
        assert action in kept
        assert "delete" not in kept
        assert len(pack.proposals) == 4
        assert pack.dropped == 2

        keys = install_proposals(session, pack.proposals)
        assert len(keys) == 4
        # additive 容器：独立键，不动既有 pending_proposals
        assert len(session.pending_alignments) == 4
        assert session.pending_proposals == {}

        before_graph = copy.deepcopy(graph)
        before_archive = len(session.open_question_archive)

        result = resolve_alignment(session, keys[0], accept=True)
        assert result["applied"] is True
        # 应用后：提案出池 + open_question 归档（确定性）
        assert len(session.pending_alignments) == 3
        assert len(session.open_question_archive) == before_archive + 1
        rec = session.open_question_archive[-1]
        assert rec["status"] == "answered"
        # LLM 零直写图谱：图谱字典逐字节不变
        assert graph == before_graph

    def test_actions_enum_closed_verbatim(self):
        assert ALIGN_ACTIONS == ("link", "dedupe", "contradict", "update")


# ── 确定性校验器：唯一闸门 ──────────────────────────────────────────────────


class TestDeterministicGate:
    def test_malformed_items_dropped_not_crash(self):
        graph = make_graph()
        provider = SyncStubProvider({
            "proposals": [
                "裸字符串不是 dict",
                {"action": "link"},  # 缺 target/content
                {"action": 42, "target": "世界本体", "content": "x"},  # 类型坏
                {"action": "link", "target": "世界本体",
                 "content": "待补充"},  # 占位内容
                {"action": "link", "target": "世界本体",
                 "content": "合法", "quote": "q"},
            ],
        })
        pack = AlignmentProposer(provider).propose(graph, "任意输入")
        assert len(pack.proposals) == 1
        assert pack.proposals[0].content == "合法"

    def test_no_llm_provider_degrades_empty(self):
        pack = AlignmentProposer(None).propose(make_graph(), "任意输入")
        assert pack.proposals == []
        assert pack.note != ""

    def test_llm_failure_degrades_empty(self):
        class Boom:
            def chat_json(self, messages: Any) -> Any:
                raise RuntimeError("boom")

        pack = AlignmentProposer(Boom()).propose(make_graph(), "x")
        assert pack.proposals == []
        assert "boom" in pack.note or pack.note

    def test_no_graph_returns_empty(self):
        provider = SyncStubProvider({"proposals": [{"action": "link", "target": "x", "content": "y"}]})
        pack = AlignmentProposer(provider).propose({}, "x")
        assert pack.proposals == []


# ── LLM 零直写断言（D21⑬ 铁律） ────────────────────────────────────────────


class TestNoLlmWrite:
    def test_llm_output_never_reaches_graph_write_path(self):
        """FakeLLM 注入含非法目标提案：LLM 输出仅能到达提案池，
        无法触达图谱写入路径——accept 应用后图谱仍逐字节不变。"""
        graph = make_graph()
        before = copy.deepcopy(graph)
        session = make_session()
        # 恶意 payload：试图注入新节点 + 非法目标
        provider = SyncStubProvider({
            "proposals": [
                {"action": "update", "target": "恶意注入节点",
                 "content": "把这条写进图谱", "quote": "写进去"},
                {"action": "link", "target": "世界本体",
                 "content": "合法提案", "quote": "q"},
            ],
        })
        pack = AlignmentProposer(provider).propose(graph, "x")
        assert [p.target for p in pack.proposals] == ["世界本体"]

        keys = install_proposals(session, pack.proposals)
        resolve_alignment(session, keys[0], accept=True)

        assert graph == before
        assert "恶意注入节点" not in graph["nodes"]

    def test_decline_zero_side_effects(self):
        graph = make_graph()
        before = copy.deepcopy(graph)
        session = make_session()
        provider = SyncStubProvider(_payload_all_four())
        pack = AlignmentProposer(provider).propose(graph, "x")
        keys = install_proposals(session, pack.proposals)

        result = resolve_alignment(session, keys[0], accept=False)
        assert result["applied"] is False
        assert len(session.pending_alignments) == 3
        assert session.open_question_archive == []
        assert graph == before

    def test_resolve_unknown_key_not_found(self):
        session = make_session()
        result = resolve_alignment(session, "align-999", accept=True)
        assert result["applied"] is False
        assert result["error"] == "not_found"


# ── stale 影响预警：下游产物清单 ────────────────────────────────────────────


class TestStaleWarning:
    def test_build_stale_warning_lists_downstream(self, tmp_path):
        db = str(tmp_path / "registry.db")
        stale_marker.ensure_registry(db)
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-W1-v1",
            stage="W", instance_no=1, version=1,
        )
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-M1-S1-v1",
            stage="M", instance_no=1, version=1,
            parent_graph_code="IP0001-W1-v1",
        )
        warning = build_stale_warning("IP0001-W1-v1", registry_db=db)
        # 「将使 … 过期」型文案 + 下游产物清单
        assert any("IP0001-W1-v1" in w and "过期" in w for w in warning)
        assert any("IP0001-M1-S1-v1" in w for w in warning)

    def test_no_children_empty_warning(self, tmp_path):
        db = str(tmp_path / "registry.db")
        stale_marker.ensure_registry(db)
        assert build_stale_warning("IP0001-W1-v9", registry_db=db) == []

    def test_install_attaches_warning_to_proposal(self, tmp_path):
        db = str(tmp_path / "registry.db")
        stale_marker.ensure_registry(db)
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-W1-v1",
            stage="W", instance_no=1, version=1,
        )
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-M1-S1-v1",
            stage="M", instance_no=1, version=1,
            parent_graph_code="IP0001-W1-v1",
        )
        session = make_session()
        session.ip_code = "IP0001"
        provider = SyncStubProvider({
            "proposals": [
                {"action": "update", "target": "世界本体",
                 "content": "修改根基设定", "quote": "q",
                 "graph_code": "IP0001-W1-v1"},
            ],
        })
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        keys = install_proposals(session, pack.proposals, registry_db=db)
        entry = session.pending_alignments[keys[0]]
        proposal = entry["proposal"]
        assert any("IP0001-M1-S1-v1" in w for w in proposal.stale_warning)

    def test_accept_marks_downstream_stale_deterministically(self, tmp_path):
        db = str(tmp_path / "registry.db")
        stale_marker.ensure_registry(db)
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-W1-v1",
            stage="W", instance_no=1, version=1,
        )
        stale_marker.register_graph(
            db, user_id="u1", graph_code="IP0001-M1-S1-v1",
            stage="M", instance_no=1, version=1,
            parent_graph_code="IP0001-W1-v1",
        )
        session = make_session()
        provider = SyncStubProvider({
            "proposals": [
                {"action": "update", "target": "世界本体",
                 "content": "修改", "quote": "q",
                 "graph_code": "IP0001-W1-v1"},
            ],
        })
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        keys = install_proposals(session, pack.proposals)
        resolve_alignment(session, keys[0], accept=True, registry_db=db)
        # 确定性应用：下游产物被标 stale（复用 stale_marker 传播）
        assert stale_marker.is_stale(db, "IP0001-M1-S1-v1") is True
        # decline 路径对照：不标 stale 在 test_decline_zero_side_effects 覆盖


# ── 提案文案说人话（引原话转述，不报模块/字段名） ───────────────────────────


class TestPlainLanguageCopy:
    def test_render_contains_quote_no_bare_keys(self):
        graph = make_graph()
        session = make_session()
        provider = SyncStubProvider(_payload_all_four())
        pack = AlignmentProposer(provider).propose(graph, "x")
        keys = install_proposals(session, pack.proposals)
        for k in keys:
            p = session.pending_alignments[k]["proposal"]
            text = render_proposal(p)
            # 引原话转述
            assert p.quote in text or p.content in text
            # 不报模块/字段名：无裸 "{mid}." 形态（G5 同款雷区）
            assert "世界本体." not in text
            assert "d:" not in text


# ── F2 补测：边界分支（目标别名 / 校验闸门上限 / 降级路径） ─────────────────


class TestGraphTargetKeysBoundaries:
    def test_non_dict_graph_returns_empty_set(self):
        from app.domains.creation.a1.alignment_flow import graph_target_keys

        assert graph_target_keys(None) == set()  # type: ignore[arg-type]
        assert graph_target_keys("junk") == set()  # type: ignore[arg-type]

    def test_edges_fallback_and_non_dict_entries(self):
        """边无 key → source->target 兜底；非 dict 边跳过。"""
        from app.domains.creation.a1.alignment_flow import graph_target_keys

        graph = {
            "nodes": {"a": {"title": "A"}},
            "edges": [
                None,  # 非 dict：跳过
                {"key": "", "source": "a", "target": "a"},  # 空 key → 兜底
                {"key": 42, "source": "a", "target": "a"},  # 非 str key → 兜底
            ],
        }
        keys = graph_target_keys(graph)
        assert "a" in keys
        assert "a->a" in keys


class TestTargetDisplayAlias:
    def _render_with_graph(self, node: dict[str, Any], target: str) -> str:
        from app.domains.creation.a1.alignment_flow import AlignProposal, render_proposal

        p = AlignProposal(action="link", target=target, content="说明")
        return render_proposal(p, graph={"nodes": {target: node}})

    def test_title_used_as_alias(self):
        text = self._render_with_graph({"title": "灵潮潮汐"}, "t1")
        assert "「灵潮潮汐」" in text

    def test_description_excerpt_when_no_title(self):
        text = self._render_with_graph({"title": "", "description": "灵潮的周期涨落"}, "t2")
        assert "灵潮的周期涨落" in text

    def test_empty_node_generic_alias(self):
        text = self._render_with_graph({"title": "", "description": ""}, "t3")
        assert "一条已有记录" in text

    def test_unknown_target_generic_alias(self):
        text = self._render_with_graph({}, "missing-target")
        assert "一条已有记录" in text


class TestGateMaxAndWhitespace:
    def test_whitespace_only_content_dropped(self):
        from app.domains.creation.a1.alignment_flow import validate_raw_proposals

        valid, dropped = validate_raw_proposals(
            make_graph(),
            [{"action": "link", "target": "世界本体", "content": "   "}],
        )
        assert valid == []
        assert dropped == 1

    def test_more_than_five_proposals_overflow_dropped(self):
        """闸门上限 5：第 6 条起确定性丢弃（不计入提案池）。"""
        from app.domains.creation.a1.alignment_flow import (
            ALIGN_MAX_PROPOSALS,
            validate_raw_proposals,
        )

        raw = [
            {"action": "link", "target": "世界本体", "content": f"合法提案 {i}"}
            for i in range(ALIGN_MAX_PROPOSALS + 2)
        ]
        valid, dropped = validate_raw_proposals(make_graph(), raw)
        assert len(valid) == ALIGN_MAX_PROPOSALS
        assert dropped == 2


class TestRegistryChildrenDegrade:
    def test_empty_db_path_returns_empty(self):
        from app.domains.creation.a1.alignment_flow import _registry_children

        assert _registry_children("", "IP0001-W1-v1") == []

    def test_connect_failure_returns_empty_not_crash(self, tmp_path):
        """registry_db 指向目录 → sqlite 连接失败降级空清单。"""
        from app.domains.creation.a1.alignment_flow import _registry_children

        assert _registry_children(str(tmp_path), "IP0001-W1-v1") == []

    def test_stale_warning_children_without_code_no_downstream_line(self, tmp_path):
        """下游行 graph_code 为空 → 不追加「受影响的下游产物」行（分支覆盖）。"""
        import sqlite3

        from app.domains.creation.a1.alignment_flow import build_stale_warning

        db = str(tmp_path / "registry.db")
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE graph_registry "
            "(graph_code TEXT, status TEXT, parent_graph_code TEXT)"
        )
        conn.execute(
            "INSERT INTO graph_registry VALUES ('', 'done', 'IP0001-W1-v1')"
        )
        conn.commit()
        conn.close()
        warning = build_stale_warning("IP0001-W1-v1", registry_db=db)
        assert any("过期" in w for w in warning)
        assert not any(w.startswith("受影响的下游产物") for w in warning)


class TestProposeDegradeShapes:
    def test_async_provider_supported(self):
        """异步 provider：chat_json 返回 awaitable → asyncio.run 消费。"""

        class AsyncProvider:
            def __init__(self, payload: Any) -> None:
                self._payload = payload

            async def chat_json(self, messages: Any) -> Any:
                return self._payload

        provider = AsyncProvider({
            "proposals": [
                {"action": "link", "target": "世界本体", "content": "合法", "quote": "q"}
            ],
        })
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        assert len(pack.proposals) == 1

    def test_non_dict_response_degrades(self):
        provider = SyncStubProvider(["not", "a", "dict"])
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        assert pack.proposals == []
        assert "形状不符" in pack.note

    def test_proposals_not_a_list_degrades(self):
        provider = SyncStubProvider({"proposals": {"action": "link"}})
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        assert pack.proposals == []
        assert "形状不符" in pack.note

    def test_all_filtered_note_explains(self):
        provider = SyncStubProvider({
            "proposals": [
                {"action": "delete", "target": "世界本体", "content": "x"}
            ],
        })
        pack = AlignmentProposer(provider).propose(make_graph(), "x")
        assert pack.proposals == []
        assert "无有效建议" in pack.note


class TestInstallKeyCollision:
    def test_existing_key_gets_suffixed(self):
        """提案键冲突 → 加后缀不覆盖既有提案（additive 容器纪律）。"""
        session = make_session()
        from app.domains.creation.a1.alignment_flow import AlignProposal

        session.pending_alignments["align-001"] = {"proposal": "既有的"}
        keys = install_proposals(session, [AlignProposal(action="link", target="世界本体", content="c")])
        assert keys[0] != "align-001"
        assert session.pending_alignments["align-001"]["proposal"] == "既有的"


class TestResolveIdempotentArchive:
    def test_accept_with_preexisting_archive_entry_skips_duplicate(self):
        """同 id 归档已存在 → 不重复追加（幂等分支）。"""
        from app.domains.creation.a1.alignment_flow import AlignProposal, install_proposals

        session = make_session()
        keys = install_proposals(
            session, [AlignProposal(action="link", target="世界本体", content="c", quote="q")]
        )
        # 预置同 id 归档记录
        from app.domains.creation.a1.alignment_flow import render_proposal

        session.open_question_archive.append({
            "id": f"oq-align-{keys[0]}",
            "question": render_proposal(session.pending_alignments[keys[0]]["proposal"]),
            "status": "answered",
            "answer": "旧答案",
            "source_hint": "alignment:link",
        })
        before = len(session.open_question_archive)
        result = resolve_alignment(session, keys[0], accept=True)
        assert result["applied"] is True
        assert len(session.open_question_archive) == before  # 未重复追加
        assert session.open_question_archive[-1]["answer"] == "旧答案"


class TestRenderEdgeForms:
    def test_render_without_quote_omits_quote_segment(self):
        from app.domains.creation.a1.alignment_flow import AlignProposal, render_proposal

        text = render_proposal(AlignProposal(action="dedupe", target="x", content="重复记录"))
        assert "你说过" not in text
        assert "重复记录" in text

    def test_render_appends_stale_warning(self):
        from app.domains.creation.a1.alignment_flow import AlignProposal, render_proposal

        p = AlignProposal(
            action="update", target="x", content="改这条",
            stale_warning=["这项修改会使已生成的成果「IP0001-W1-v1」过期"],
        )
        text = render_proposal(p)
        assert "过期" in text
