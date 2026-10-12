"""L3 答案树化契约红测（波次二批 B 第一步——先红后绿，零实现）。

契约锚点：
- AnswerNode 权威 schema（docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md
  + SYSTEM_DESIGN_SPEC_v6 §2.6 v6.3）：text / children[] / source 三字段。
- L3 答案以 AnswerNode children 挂 L2 锚下（现行实现 = guide_engine D23 区
  answer_view/_apply_fills 的多值字段机制向全树扩展——T5 转绿落点）。
- 57 个新 L3 答案不进 A1Session 平面字段：answers dict 键仍为 "module.field"
  既有宇宙（树锚定位），写入后 flat 键集合零新增。
- 同类自动归并语义在 L3 层沿用 D23 判定（等价/补充/矛盾——guide_engine
  语义路由同构）。

红测纪律：锁契约不锁实现——新入口经 getattr 发现（断言存在性失败 =
AssertionError，非 ImportError）；测试不落任何修复实现。
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from app.domains.creation.a1 import guide_engine
from app.domains.creation.a1.guide_engine import (
    A1Session,
    AnswerNode,
    answer_view,
    resolve_proposal,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys
from app.domains.creation.seed.story_modules import (
    LIST_CAPS,
    THREE_TIER_TREE,
    VS_ENUM,
)

# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

#: T5 候选入口名（契约面：接受 (session, l3_id, value, **kw) 的树写入口）。
_L3_WRITER_CANDIDATES = (
    "apply_l3_fill",
    "write_l3_answer",
    "fill_l3",
    "l3_fill",
    "apply_fill_l3",
)

#: T5 候选读入口名（树读：给定 l3_id 返回 AnswerNode / 渲染串）。
_L3_READER_CANDIDATES = (
    "read_l3_answer",
    "l3_answer",
    "get_l3_answer",
    "l3_read",
)


def _discover(names: tuple[str, ...]) -> Callable[..., Any] | None:
    for n in names:
        fn = getattr(guide_engine, n, None)
        if callable(fn):
            return fn
    return None


def _l3_ids() -> set[str]:
    """收集树内全部 L3 id（L1→L2→L3 三层遍历）。"""
    out: set[str] = set()
    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:  # type: ignore[union-attr]
            for l3 in l2["l3"]:  # type: ignore[union-attr]
                out.add(l3["id"])  # type: ignore[union-attr]
    return out


#: 57 新增 L3 之一（⑤⑥稿：剧情线开场事件组），非现行 35 字段宇宙成员。
NEW_L3_ID = "daily_life"

#: 现行多值字段（D23 已落地先例，作机制锚）。
LEGACY_MULTI_KEY = "角色.key_relations"


def _session() -> A1Session:
    s = A1Session(session_id="t-l3-tree", user_id="u")
    sync_position(s)
    return s


def _flat_universe() -> set[str]:
    return set(all_subfield_keys())


# ---------------------------------------------------------------------------
# 锚（现行实现，GREEN——锁 AnswerNode schema 权威形态不漂移）
# ---------------------------------------------------------------------------


class TestAnswerNodeSchemaAnchor:
    """AnswerNode 权威三字段：text / children[] / source（v6 §2.6）。"""

    def test_three_fields_only_semantics(self):
        node = AnswerNode(text="老父亲", source="user")
        assert node.text == "老父亲"
        assert node.children == []
        assert node.source == "user"

    def test_children_recursive(self):
        node = AnswerNode(text="关系清单", children=[AnswerNode(text="老父亲")])
        assert node.children[0].children == []

    def test_answer_view_depth_first_join(self):
        node = AnswerNode(
            text="师姐",
            children=[AnswerNode(text="老父亲"), AnswerNode(text="线人女儿")],
        )
        assert answer_view(node) == "师姐；老父亲；线人女儿"


class TestTreeUniverseAnchor:
    """树宇宙锚：92 L3 / vs 闭集 / 清单帽表（T2 落库，消费契约的前提）。"""

    def test_l3_universe_contains_new_nodes(self):
        assert NEW_L3_ID in _l3_ids()

    def test_every_l3_has_vs_in_closed_enum(self):
        for l1 in THREE_TIER_TREE:
            for l2 in l1["l2"]:  # type: ignore[union-attr]
                for l3 in l2["l3"]:  # type: ignore[union-attr]
                    assert l3["vs"] in VS_ENUM  # type: ignore[union-attr]

    def test_list_caps_keys_cover_list_positions(self):
        assert LIST_CAPS["conflict"] == 6
        assert LIST_CAPS["existence"] == 12


# ---------------------------------------------------------------------------
# 红：L3 答案树化写入/读回 + 平面字段零新增
# ---------------------------------------------------------------------------


class TestL3AnswerWriteRead:
    """57 新 L3 答案可写入且可读回；A1Session 平面字段键零新增。"""

    def test_l3_writer_entry_exists(self):
        assert _discover(_L3_WRITER_CANDIDATES) is not None, (
            "guide_engine 缺 L3 树写入口（候选：%s）——批 B 引擎接线未落地"
            % ", ".join(_L3_WRITER_CANDIDATES)
        )

    def test_l3_reader_entry_exists(self):
        assert _discover(_L3_READER_CANDIDATES) is not None, (
            "guide_engine 缺 L3 树读入口（候选：%s）" % ", ".join(_L3_READER_CANDIDATES)
        )

    def test_new_l3_answer_roundtrip(self):
        write = _discover(_L3_WRITER_CANDIDATES)
        read = _discover(_L3_READER_CANDIDATES)
        s = _session()
        write(s, NEW_L3_ID, "破局前夜他在修钟表铺的老座钟")  # type: ignore[misc]
        got = read(s, NEW_L3_ID)  # type: ignore[misc]
        assert answer_view(got) == "破局前夜他在修钟表铺的老座钟"

    def test_flat_answer_keys_zero_growth(self):
        """写入 L3 后 answers 的平面键 ⊆ 既有 module.field 宇宙。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        s = _session()
        write(s, NEW_L3_ID, "日常质感答案")  # type: ignore[misc]
        flat = {k for k, v in s.answers.items() if isinstance(v, str)}
        assert flat <= _flat_universe(), (
            f"L3 答案泄漏进平面字段：{flat - _flat_universe()}"
        )

    def test_l3_answer_hangs_under_l2_anchor(self):
        """L3 答案以 AnswerNode children 形态挂 L2 锚下（树定位可回放）。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        s = _session()
        write(s, NEW_L3_ID, "钟表铺日常")  # type: ignore[misc]
        # 树内定位：任一 AnswerNode 的 children 中含该答案文本。
        found = [
            v for v in s.answers.values()
            if isinstance(v, AnswerNode)
            and any(c.text == "钟表铺日常" for c in v.children)
        ]
        assert found, "L3 答案未以 children 形态挂在任何 AnswerNode 锚下"


class TestL3LegacySemanticRouting:
    """D23 语义判定在 L3 层沿用：等价/补充/矛盾 同构路由。"""

    def _write(self, s: A1Session, value: str, relation: str | None = None):
        write = _discover(_L3_WRITER_CANDIDATES)
        return write(s, NEW_L3_ID, value, relation=relation)  # type: ignore[misc]

    def test_complement_appends_child(self):
        s = _session()
        self._write(s, "第一条日常")
        self._write(s, "第二条日常", relation="complement")
        read = _discover(_L3_READER_CANDIDATES)
        node = read(s, NEW_L3_ID)  # type: ignore[misc]
        texts = [c.text for c in node.children]
        assert "第二条日常" in texts

    def test_equivalent_merges_not_duplicates(self):
        s = _session()
        self._write(s, "修钟表的日常")
        self._write(s, "修钟表的日常", relation="equivalent")
        read = _discover(_L3_READER_CANDIDATES)
        node = read(s, NEW_L3_ID)  # type: ignore[misc]
        assert answer_view(node).count("修钟表的日常") <= 1 or node.children == []

    def test_conflict_goes_to_proposal_flow(self):
        s = _session()
        self._write(s, "日常是平静的")
        self._write(s, "日常早被撕裂", relation="conflict")
        assert s.pending_proposals, "矛盾语义未走 D23 三选一提议流"
        key = next(iter(s.pending_proposals))
        result = resolve_proposal(s, key, "drop")
        assert result["applied"] is False
