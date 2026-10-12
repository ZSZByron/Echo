"""清单追加循环停驻状态机契约红测（⑤稿 §9 + D24 先例——先红后绿，零实现）。

状态机契约（list_thread_key / list_thread_turns 已由批 A 落库，待消费）：
- 进入：用户在 list 位点（如 角色.key_relations）补充新条目 →
  list_thread_key 置位该位点、list_thread_turns 推进。
- 四出口：
  ① 直选退出——用户直接回答当前问 → 复位 ""/0
  ② 跳过退出——"跳过" → 复位
  ③ 帽满退出——追加达 LIST_CAPS[key] → 帽满话术 + 走 D23 提议流归并
  ④ 话题离开退出——说别的 → 归档复位
- 两档帽：6 帽位点（conflict/faction_type 等 12 键）/ 12 帽位点
  （existence/key_nodes/material_pool）。12 帽位点的追加不得被 D23 旧
  ANSWER_CHILDREN_CAP=6 提前截断。
- 等价归并达帽走 D23 提议流（resolve_proposal 区）。
- turns 每轮推进防卡死（D24 knowledge_thread_turns 先例）。

病理两幕（skipif 预埋——批 B 引擎接线后自动转活）：
- 老父亲追加：key_relations 已答"老父亲"再补充 → 追加进关系清单
  （非弹三连问、非单槽覆盖）
- 第 3 张关系卡：multi 追加行为

红测纪律：全部引擎级（A1Session + handle_message + FakeInterviewer），
不起 TestClient；不写任何修复实现。
"""
from __future__ import annotations

import inspect
from typing import Any

import pytest

from app.domains.creation.a1 import guide_engine
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
    resolve_proposal,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys
from app.domains.creation.seed.story_modules import LIST_CAPS

# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

RELATION_KEY = "角色.key_relations"

_WORLD_CONFLICT_KEY = next(
    k for k in all_subfield_keys() if k.endswith(".conflict")
)  # 文明与社会.conflict（6 帽位点，现行字段宇宙成员）

_WORLD_EXISTENCE_KEY = next(
    k for k in all_subfield_keys() if k.endswith(".existence")
)  # 世界本体.existence（12 帽位点，现行字段宇宙成员）

_DISTINCT_APPENDS = [
    "老父亲——他这辈子最亏欠的人",
    "叛出师门的师姐——互为唯一软肋",
    "收留他的钟表铺老板——无言的恩情",
    "线人的女儿——他偷偷照顾的孩子",
    "死对头捕头——公私两面的缠斗",
    "早逝的师兄——名与实的枷锁",
        "蒙面旧客——第七个闯入者",
    "酒馆老板娘——消息集散地",
    "哑巴学徒——沉默的见证者",
    "远房侄子——血脉的最后牵连",
    "旧日同门——反目的镜子",
    "神秘债主——悬而未决的旧账",
]


def _story_session() -> A1Session:
    s = A1Session(
        session_id="t-list-loop",
        user_id="u",
        recipe_id="plot",
        recipe_modules=["剧情", "角色"],
    )
    sync_position(s)
    return s


def _append(session: A1Session, value: str, subfield: str = "key_relations",
            module: str = "角色") -> dict[str, Any]:
    """一轮"补充新条目"：complement relation 追加进清单位点。"""
    fake = FakeInterviewer(fills=[InterviewFill(
        module=module, subfield=subfield, value=value, relation="complement",
    )])
    return handle_message(session, value, fake)


def _list_thread_wired() -> bool:
    """批 B 接线探测：_handle_message_impl 是否已消费 list_thread（skipif 门）。"""
    src = inspect.getsource(guide_engine._handle_message_impl)
    return "list_thread" in src


# ---------------------------------------------------------------------------
# 红：停驻进入 + turns 推进
# ---------------------------------------------------------------------------


class TestThreadEntry:
    def test_append_parks_thread(self):
        s = _story_session()
        _append(s, _DISTINCT_APPENDS[0])
        assert s.list_thread_key == "key_relations", (
            f"list_thread_key={s.list_thread_key!r}——停驻未置位"
        )

    def test_turns_advance_each_round(self):
        s = _story_session()
        _append(s, _DISTINCT_APPENDS[0])
        _append(s, _DISTINCT_APPENDS[1])
        assert s.list_thread_turns >= 2, (
            f"list_thread_turns={s.list_thread_turns}——未逐轮推进（防卡死契约）"
        )


# ---------------------------------------------------------------------------
# 红：四出口
# ---------------------------------------------------------------------------


class TestFourExits:
    def test_direct_answer_exit(self):
        """出口①：用户直接回答当前问 → 复位 ""/0。"""
        s = _story_session()
        _append(s, _DISTINCT_APPENDS[0])
        assert s.list_thread_key == "key_relations"  # 停驻前置（红锚）
        fake = FakeInterviewer(fills=[InterviewFill(
            module="角色", subfield="key_relations", value="直答内容",
        )])
        handle_message(s, "直答内容", fake)
        assert (s.list_thread_key, s.list_thread_turns) == ("", 0)

    def test_skip_exit(self):
        """出口②："跳过" → 复位。"""
        s = _story_session()
        _append(s, _DISTINCT_APPENDS[0])
        assert s.list_thread_key == "key_relations"  # 停驻前置（红锚）
        handle_message(s, "跳过", FakeInterviewer())
        assert (s.list_thread_key, s.list_thread_turns) == ("", 0)

    def test_topic_leave_exit(self):
        """出口④：说别的（无 fills 的闲聊/知识话题）→ 归档复位。"""
        s = _story_session()
        _append(s, _DISTINCT_APPENDS[0])
        assert s.list_thread_key == "key_relations"  # 停驻前置（红锚）
        handle_message(s, "顺便问下，修仙小说里灵气一般怎么设定？", FakeInterviewer())
        assert (s.list_thread_key, s.list_thread_turns) == ("", 0)

    def test_cap_full_exit_via_proposal_flow(self):
        """出口③：追加达 LIST_CAPS → 帽满话术 + D23 提议流归并 + 复位。"""
        s = _story_session()
        cap = LIST_CAPS["key_relations"]
        for i in range(cap):
            _append(s, _DISTINCT_APPENDS[i % len(_DISTINCT_APPENDS)] + str(i))
        assert s.list_thread_key == "key_relations"  # 停驻前置（红锚）
        # 第 cap+1 次追加 → 帽满退出：复位 + 走提议流（等价/归并拍板）。
        result = _append(s, "第%s张新卡" % (cap + 1))
        assert s.pending_proposals or result.get("classification_proposal"), (
            "帽满后未走 D23 提议流"
        )
        assert (s.list_thread_key, s.list_thread_turns) == ("", 0)


# ---------------------------------------------------------------------------
# 红：两档帽
# ---------------------------------------------------------------------------


class TestTwoCapTiers:
    def test_six_cap_position_proposes_at_sixth(self):
        """6 帽位点（文明与社会.conflict）：前 5 次静默追加，第 6 次触发提议流。"""
        s = _story_session()
        module_id = _WORLD_CONFLICT_KEY.split(".", 1)[0]
        for i in range(5):
            _append(s, f"冲突来源 {i}——各自成势", subfield="conflict",
                    module=module_id)
        assert not s.pending_proposals, "6 帽位点未满即弹提议"
        _append(s, "冲突来源 5——第六方势力", subfield="conflict", module=module_id)
        assert s.pending_proposals, "第 6 次追加未触发帽满提议流"

    def test_twelve_cap_position_not_early_capped(self):
        """12 帽位点（世界本体.existence）：旧 ANSWER_CHILDREN_CAP=6 不得提前截断。"""
        s = _story_session()
        module_id = _WORLD_EXISTENCE_KEY.split(".", 1)[0]
        for i in range(8):
            _append(s, f"存在物 {i}——形态各异", subfield="existence", module=module_id)
        # 第 7、8 次追加仍应静默入清单（12 帽），不得在 6 处提前弹提议。
        assert not s.pending_proposals, (
            "12 帽位点在第 6 处被旧 ANSWER_CHILDREN_CAP 提前截断"
        )


# ---------------------------------------------------------------------------
# 红：等价归并达帽走提议流 + turns 防卡死
# ---------------------------------------------------------------------------


class TestMergeAtCapAndAntiStall:
    def test_equivalent_merge_at_cap_goes_to_proposal(self):
        s = _story_session()
        cap = LIST_CAPS["key_relations"]
        for i in range(cap):
            _append(s, _DISTINCT_APPENDS[i % len(_DISTINCT_APPENDS)] + str(i))
        assert s.list_thread_key == "key_relations"  # 停驻前置（红锚）
        # 帽满后等价归并请求 → 提议流（resolve_proposal 区可拍板）。
        fake = FakeInterviewer(fills=[InterviewFill(
            module="角色", subfield="key_relations",
            value="老父亲的新细节", relation="equivalent",
        )])
        handle_message(s, "老父亲还有新细节", fake)
        assert s.pending_proposals, "帽满后等价归并未入提议流"
        key = next(iter(s.pending_proposals))
        assert "options" in s.pending_proposals[key]
        resolve_proposal(s, key, "drop")

    def test_turns_never_stall_forever(self):
        """D24 先例：每轮推进——多轮停驻后 turns 单调递增，无无限停驻。"""
        s = _story_session()
        seen: list[int] = []
        for i in range(4):
            _append(s, _DISTINCT_APPENDS[i])
            seen.append(s.list_thread_turns)
        assert seen == sorted(seen) and len(set(seen)) == len(seen), (
            f"turns 序列 {seen}——存在零推进轮（卡死风险）"
        )


# ---------------------------------------------------------------------------
# 病理两幕（skipif 预埋：批 B 接线后自动转活）
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _list_thread_wired(),
    reason="批 B 未接线：_handle_message_impl 尚未消费 list_thread 状态机",
)
class TestPathologicalFatherAppend:
    """病理一：老父亲追加——已答"老父亲"后再补充新信息。"""

    def test_append_into_relations_list(self):
        s = _story_session()
        _append(s, "老父亲——他这辈子最亏欠的人")
        # 再补充老父亲的**新信息**：追加进关系清单（非三连问、非单槽覆盖）。
        fake = FakeInterviewer(fills=[InterviewFill(
            module="角色", subfield="key_relations",
            value="老父亲临终托付了一把钥匙", relation="complement",
        )])
        result = handle_message(s, "老父亲还留了把钥匙", fake)
        node = s.answers.get(RELATION_KEY)
        rendered = str(node)
        assert "老父亲临终托付" in rendered, "新信息未追加进关系清单"
        # 非单槽覆盖：首批条目仍在。
        assert "最亏欠的人" in rendered
        # 非三连问拦截：不产生待拍板提案。
        assert not s.pending_proposals or result.get("classification_proposal")


@pytest.mark.skipif(
    not _list_thread_wired(),
    reason="批 B 未接线：multi 追加停驻循环未启用",
)
class TestPathologicalThirdRelationCard:
    """病理二：第 3 张关系卡——multi 追加行为（清单条目 ≥3 不劣化）。"""

    def test_third_card_appends(self):
        s = _story_session()
        for i in range(2):
            _append(s, _DISTINCT_APPENDS[i])
        _append(s, _DISTINCT_APPENDS[2])
        node = s.answers.get(RELATION_KEY)
        rendered = str(node)
        for snippet in (_DISTINCT_APPENDS[0], _DISTINCT_APPENDS[1],
                        _DISTINCT_APPENDS[2]):
            assert snippet in rendered, f"第 3 张卡丢失：{snippet}"
