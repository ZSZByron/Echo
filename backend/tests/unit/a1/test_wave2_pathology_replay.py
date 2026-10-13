"""波次二批 E-2：四幕病理回归自动化（端点级重放）+ 交叉烟测。

四幕病理（历史人工复现案例 → TestClient 自动化；LLM 一律确定性 stub，
monkeypatch ``a1_routes._get_interviewer``——D23 F3 先例范式）：

- 幕一「老父亲」：M11 关键关系答"老父亲"后补充新信息（"他其实是我师父"）
  → 追加进关系卡清单（children +1），非弹三选一提议、非单槽覆盖旧答案。
- 幕二「支线结局」：支线卡衔接点/结局槽落值（side_link_point/side_ending），
  主线答案不被污染（2026-10-08 老伤闭环）。新 L3 位点引擎直调
  ``apply_l3_fill``（chat fills 只达旧 35 字段平面宇宙，与 T5 先例一致）。
- 幕三「这是分支」：分支双终点（"要么成仙要么入魔"）→ branch_trees 双终点
  槽分流（success_path/failure_path 各自 from/to 承载，非压缩单值）。
- 幕四「清单追加循环」：关系卡追加 ×3 → 帽行为（LIST_CAPS 驱动）+ 等价
  归并达帽提议流触发 + 直答/跳过打断后 list_thread 复位全路径。

交叉烟测：一幕内混合触发——讨论镜像一轮 → 投递入架 → 知识态 → 直选 →
清单追加——四个状态机（knowledge_thread/mirror_thread/list_thread/
material_pool）互不复位互不污染（options_key 对称复位的全通道版）。
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import (
    A1Session,
    apply_l3_fill,
    handle_message,
    l3_value_parts,
    read_l3_answer,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
)
from app.domains.creation.seed.story_modules import LIST_CAPS
from app.main import app

RELATION_KEY = "角色.key_relations"


# ---------------------------------------------------------------------------
# 确定性 stub（照 D23 F3：monkeypatch a1_routes._get_interviewer）
# ---------------------------------------------------------------------------


class _ScriptedStub:
    """按轮次弹出预设 InterviewResult 的确定性 interviewer 替身。

    每轮配置 = dict(fills=[...], mirror=..., delivery=..., knowledge_used=...,
    guidance_reply=...)。零真实 LLM。
    """

    def __init__(self, rounds: list[dict[str, Any]]):
        self._rounds = list(rounds)
        self.calls = 0

    def interview(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        self.calls += 1
        assert self._rounds, "stub 轮次耗尽（脚本轮数 < 实际 interview 调用数）"
        cfg = self._rounds.pop(0)
        return InterviewResult.model_construct(
            fills=list(cfg.get("fills") or []),
            guidance_reply=cfg.get("guidance_reply", "好的，记下了思路。"),
            knowledge_used=bool(cfg.get("knowledge_used")),
            delivery=bool(cfg.get("delivery")),
            mirror=bool(cfg.get("mirror")),
            reanchor=bool(cfg.get("reanchor")),
        )

    def classify_confirm_intent(self, old: str, new: str, reply: str) -> str:  # noqa: ARG002
        return "other"

    def set_pending_open_question(self, question: dict) -> None:  # noqa: ARG002
        pass

    def take_open_question_answered(self) -> dict | None:
        return None

    def suggest_examples(self, session: Any, module_id: str, subfield_id: str) -> list[str]:  # noqa: ARG002
        return ["示例一", "示例二", "示例三"]

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        return InterviewResult.model_construct(
            fills=[], guidance_reply="再说说看？",
        )


def _fill(value: str, relation: str | None = None, module: str = "角色",
          subfield: str = "key_relations",
          merged_value: str | None = None) -> InterviewFill:
    return InterviewFill(
        module=module, subfield=subfield, value=value, relation=relation,
        merged_value=merged_value,
    )


def _one_round(client: TestClient, session_id: str, text: str,
               stub: _ScriptedStub, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(a1_routes, "_get_interviewer", lambda: stub)
    resp = client.post(
        "/api/a1/chat", json={"session_id": session_id, "message": text},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_wave2", "seed_id": 1})
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 幕一「老父亲」：补充新信息 → 关系卡清单追加（非提议、非覆盖）
# ---------------------------------------------------------------------------


class TestAct1OldFatherSupplement:
    def test_supplement_appends_not_overwrites_not_proposes(
        self, client, started, monkeypatch,
    ):
        sid = started["session_id"]
        stub = _ScriptedStub([
            {"fills": [_fill("老父亲", relation="complement")]},
            {"fills": [_fill("他其实是我师父", relation="complement")]},
        ])
        # 第一轮：答"老父亲" → 直写落库（空槽直写）
        out1 = _one_round(client, sid, "我最放不下的是我的老父亲", stub, monkeypatch)
        assert out1["proposals"] == []
        session = a1_routes._SESSIONS[sid]
        assert session.answers[RELATION_KEY] == "老父亲"

        # 第二轮：补充"他其实是我师父" → 追加进关系卡清单
        out2 = _one_round(client, sid, "他其实是我师父", stub, monkeypatch)
        assert out2["proposals"] == []
        val = session.answers[RELATION_KEY]
        # 正断言：children +1，两条都在
        assert val.text == "老父亲"
        assert [c.text for c in val.children] == ["他其实是我师父"]
        # 反断言：非弹三选一提议
        assert session.pending_proposals == {}
        # 反断言：非单槽覆盖——旧答案原样保留在条目首
        assert "老父亲" in str(out2["file_diff"])

    def test_plain_contradiction_would_propose(self, client, started, monkeypatch):
        """对照面：非 complement（矛盾语义）才走三选一——补充语义不弹问。"""
        sid = started["session_id"]
        stub = _ScriptedStub([
            {"fills": [_fill("老父亲", relation="complement")]},
            {"fills": [_fill("老父亲早就过世了", relation="conflict")]},
        ])
        _one_round(client, sid, "我最放不下的是我的老父亲", stub, monkeypatch)
        _one_round(client, sid, "不对，老父亲早就过世了", stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        assert session.answers[RELATION_KEY] == "老父亲"  # 拦截不落库
        assert len(session.pending_proposals) == 1  # 三选一提议在场


# ---------------------------------------------------------------------------
# 幕二「支线结局」：落支线卡衔接点/结局槽，主线不被污染
# ---------------------------------------------------------------------------


class TestAct2SideEndingSlots:
    def test_side_link_point_and_ending_slots_filled(self):
        session = A1Session(session_id="s_act2", user_id="u")
        sync_position(session)
        # 用户说"用支线结局说明主线成功"→ LLM 产出结构化 ▶ 值，确定性落槽
        apply_l3_fill(session, "side_link_point", {
            "from": "主线第3章分岔口", "to": "支线汇入主线",
        })
        apply_l3_fill(session, "side_ending", {
            "from": "支线终局", "to": "主线成功线",
        })
        # 正断言：两个 ▶ 槽位各自承载 from/to 部件
        link_parts = l3_value_parts(session, "side_link_point")
        ending_parts = l3_value_parts(session, "side_ending")
        assert link_parts == {
            "from": "主线第3章分岔口", "to": "支线汇入主线",
        }
        assert ending_parts == {
            "from": "支线终局", "to": "主线成功线",
        }
        # 反断言：主线答案不被污染（success_path 未写入）
        assert read_l3_answer(session, "success_path").text == ""
        assert l3_value_parts(session, "success_path") == {}
        # 反断言：不弹问
        assert session.pending_proposals == {}

    def test_half_filled_slot_tolerated(self):
        """半填宽容：只说结局不说衔接 → side_ending 单边承载、不报错。"""
        session = A1Session(session_id="s_act2b", user_id="u")
        sync_position(session)
        apply_l3_fill(session, "side_ending", {"to": "支线落幕"})
        parts = l3_value_parts(session, "side_ending")
        assert parts == {"to": "支线落幕"}
        assert session.pending_proposals == {}


# ---------------------------------------------------------------------------
# 幕三「这是分支」：分支双终点槽分流（非压缩单值）
# ---------------------------------------------------------------------------


class TestAct3BranchDualEndings:
    def test_dual_endings_carried_in_two_slots(self):
        session = A1Session(session_id="s_act3", user_id="u")
        sync_position(session)
        # "结局要么成仙要么入魔" → 双终点分流到 success_path/failure_path
        apply_l3_fill(session, "success_path", {
            "from": "开局凡人", "to": "飞升成仙",
        })
        apply_l3_fill(session, "failure_path", {
            "from": "开局凡人", "to": "堕落入魔",
        })
        # 双终点挂在 branch_trees L2 锚下（锚键 = L2 id，批B 锚键设计）
        anchor = session.answers["branch_trees"]
        sources = {c.source for c in anchor.children}
        assert {"success_path", "failure_path"} <= sources
        # 双终点各自完整承载 from/to——非压缩成单值串
        assert l3_value_parts(session, "success_path") == {
            "from": "开局凡人", "to": "飞升成仙",
        }
        assert l3_value_parts(session, "failure_path") == {
            "from": "开局凡人", "to": "堕落入魔",
        }
        # 反断言：不弹问、不丢数据
        assert session.pending_proposals == {}
        assert read_l3_answer(session, "success_path").text == "开局凡人；飞升成仙"
        assert read_l3_answer(session, "failure_path").text == "开局凡人；堕落入魔"


# ---------------------------------------------------------------------------
# 幕四「清单追加循环」：帽行为 + 等价归并达帽提议流 + 打断复位全路径
# ---------------------------------------------------------------------------


_APPENDS = [
    "老父亲——一夜白头后仍放不下儿子",
    "已叛出师门的师兄——恩怨两难",
    "青梅竹马的邻家女——唯寒的软肋",
    "授业恩师——背叛与亏欠",
    "结拜兄弟——同生共死过",
    "对头的独女——敌营里的知音",
]


class TestAct4ListAppendLoop:
    def test_three_appends_cap_driven_no_proposal(self, client, started, monkeypatch):
        assert LIST_CAPS["key_relations"] == 6  # 16 键帽表锚（批B §9.4）
        sid = started["session_id"]
        stub = _ScriptedStub([
            {"fills": [_fill(v, relation="complement")]} for v in _APPENDS[:3]
        ])
        for v in _APPENDS[:3]:
            _one_round(client, sid, v, stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        val = session.answers[RELATION_KEY]
        # 帽行为：×3 追加 = 首条 text + 2 children；turns 逐轮推进
        assert val.text == _APPENDS[0]
        assert [c.text for c in val.children] == _APPENDS[1:3]
        assert session.list_thread_key == "key_relations"
        assert session.list_thread_turns >= 3
        # 未达帽：不弹提议
        assert session.pending_proposals == {}

    def test_cap_full_complement_forces_proposal_and_resets_thread(
        self, client, started, monkeypatch,
    ):
        sid = started["session_id"]
        # 6 轮 complement 追加到 children==5（= cap-1），第 7 条触帽满提议
        rounds = [{"fills": [_fill(v, relation="complement")]} for v in _APPENDS]
        rounds.append({"fills": [_fill("第七条：义庄老主顾", relation="complement")]})
        stub = _ScriptedStub(rounds)
        for v in _APPENDS:
            _one_round(client, sid, v, stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        val = session.answers[RELATION_KEY]
        assert len(val.children) == 5  # cap-1：帽满临界
        assert session.list_thread_key == "key_relations"

        _one_round(client, sid, "第七条：义庄老主顾", stub, monkeypatch)
        # 帽满：complement 不再追加 → D23 三选一提议 + 停驻复位
        assert len(val.children) == 5  # 数据不丢、不溢帽
        assert len(session.pending_proposals) == 1
        pk, entry = next(iter(session.pending_proposals.items()))
        assert entry["options"] == ["replace", "merge", "drop"]
        assert "义庄老主顾" in entry["proposal"].new
        assert session.list_thread_key == ""
        assert session.list_thread_turns == 0

    def test_equivalent_merge_at_cap_triggers_proposal_flow(
        self, client, started, monkeypatch,
    ):
        """等价归并达帽（children >= cap-1）：不静默合并 → 提议流拍板。"""
        sid = started["session_id"]
        rounds = [{"fills": [_fill(v, relation="complement")]} for v in _APPENDS]
        rounds.append({"fills": [_fill(
            "老父亲——一夜白头仍放不下", relation="equivalent",
            merged_value="老父亲——白发人送黑发人",
        )]})
        stub = _ScriptedStub(rounds)
        for v in _APPENDS:
            _one_round(client, sid, v, stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        before = [c.text for c in session.answers[RELATION_KEY].children]

        out = _one_round(client, sid, "还是老父亲那条", stub, monkeypatch)
        # 达帽等价归并：改走提议流（非静默合并）
        assert len(session.pending_proposals) == 1
        assert out["proposals"], "帽满等价归并必须以提议形式呈现"
        # children 原样（未合并、未覆盖）
        assert [c.text for c in session.answers[RELATION_KEY].children] == before
        assert session.list_thread_key == ""  # 停驻复位（出口③）

    def test_direct_answer_interrupt_resets_thread(self, client, started, monkeypatch):
        """出口①：停驻中收到非 complement 直答 → 复位 ""/0（数据走提议流）。"""
        sid = started["session_id"]
        stub = _ScriptedStub([
            {"fills": [_fill(_APPENDS[0], relation="complement")]},
            {"fills": [_fill("替换成：孤身一人", relation="conflict")]},
        ])
        _one_round(client, sid, _APPENDS[0], stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        assert session.list_thread_key == "key_relations"

        _one_round(client, sid, "不对，他是孤身一人", stub, monkeypatch)
        assert session.list_thread_key == ""
        assert session.list_thread_turns == 0
        # 数据保护：矛盾语义走拦截，旧答案未被覆盖
        assert session.answers[RELATION_KEY] == _APPENDS[0]
        assert len(session.pending_proposals) == 1

    def test_skip_interrupt_resets_thread(self, client, started, monkeypatch):
        """出口②：显式「跳过」→ 停驻归档复位。"""
        sid = started["session_id"]
        stub = _ScriptedStub([{"fills": [_fill(_APPENDS[0], relation="complement")]}])
        _one_round(client, sid, _APPENDS[0], stub, monkeypatch)
        session = a1_routes._SESSIONS[sid]
        assert session.list_thread_key == "key_relations"
        # 跳过是确定性元命令——stub 不再被调用
        resp = client.post("/api/a1/chat", json={"session_id": sid, "message": "跳过"})
        assert resp.status_code == 200
        assert session.list_thread_key == ""
        assert session.list_thread_turns == 0


# ---------------------------------------------------------------------------
# 交叉烟测：四状态机互不复位互不污染（全通道版）
# ---------------------------------------------------------------------------


class _FlagStub:
    """handle_message 直调用 flag 化 stub（镜像/投递/知识/直选混合驱动）。"""

    def __init__(self) -> None:
        self.mirror = False
        self.delivery = False
        self.knowledge_used = False
        self.fills: list[InterviewFill] = []

    def interview(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply="好的。",
            knowledge_used=self.knowledge_used,
            delivery=self.delivery,
            mirror=self.mirror,
            reanchor=False,
        )

    def suggest_examples(self, session: Any, module_id: str, subfield_id: str) -> list[str]:  # noqa: ARG002
        return []


class TestCrossChannelSmoke:
    def test_four_state_machines_no_cross_pollution(self):
        s = A1Session(session_id="s_cross", user_id="u")
        sync_position(s)
        stub = _FlagStub()

        # ① 清单追加：list_thread 停驻
        stub.fills = [_fill(_APPENDS[0], relation="complement")]
        handle_message(s, _APPENDS[0], stub)
        assert s.list_thread_key == "key_relations"
        assert not s.mirror_thread_active and not s.knowledge_thread_active
        assert s.material_pool == []

        # ② 讨论镜像一轮：mirror 停驻；list/material 不受扰
        stub.fills, stub.mirror = [], True
        out = handle_message(s, "师父为什么要把剑留在门口？", stub)
        assert s.mirror_thread_active and s.mirror_thread_turns == 1
        assert "回到当前的问题" in out["reply"]
        assert s.list_thread_key == "key_relations"  # 互不复位
        assert s.material_pool == []
        assert not s.knowledge_thread_active

        # ③ 投递入架：material_pool +1；镜像因话题离开复位；list 不动
        stub.mirror, stub.delivery = False, True
        out = handle_message(s, "记一笔：雨夜义庄的灯笼都倒挂着", stub)
        assert "灵感架" in out["reply"]
        assert len(s.material_pool) == 1
        assert s.material_pool[0]["text"].startswith("记一笔")
        assert not s.mirror_thread_active and s.mirror_thread_turns == 0
        assert s.list_thread_key == "key_relations"

        # ④ 知识态一轮：knowledge 停驻；list_thread 知识轮豁免（不复位）
        stub.delivery, stub.knowledge_used = False, True
        out = handle_message(s, "明代义庄是怎么运转的？", stub)
        assert out["reply"].endswith("（已联网查证）")
        assert s.knowledge_thread_active and s.knowledge_thread_turns == 1
        assert s.list_thread_key == "key_relations"
        assert len(s.material_pool) == 1

        # ⑤ 直选打断：knowledge/mirror 复位 + options 对称消费；pool/list 不动
        stub.knowledge_used = False
        s.current_options = ["守夜人", "入殓师", "账房先生"]
        s.options_key = f"{s.current_module}.{s.current_subfield}"
        out = handle_message(s, "1", stub)
        assert out["reply"].startswith("已按示例记录")
        assert not s.knowledge_thread_active and s.knowledge_thread_turns == 0
        assert not s.mirror_thread_active
        assert s.current_options == [] and s.options_key == ""  # 对称复位
        assert s.list_thread_key == "key_relations"  # 直选不打断清单停驻
        assert len(s.material_pool) == 1  # 架上素材不被误清

        # ⑥ 正常清单追加轮：全通道归位——list 推进、其余三态零残留
        stub.fills = [_fill(_APPENDS[1], relation="complement")]
        handle_message(s, _APPENDS[1], stub)
        assert not s.knowledge_thread_active
        assert not s.mirror_thread_active and s.mirror_thread_turns == 0
        val = s.answers[RELATION_KEY]
        assert [c.text for c in val.children] == [_APPENDS[1]]
        assert s.list_thread_key == "key_relations"
        assert s.list_thread_turns >= 2
        assert len(s.material_pool) == 1  # 唯一素材原样（互不污染）
        assert s.pending_proposals == {}  # 无 suggested_slots → 不弹安家
