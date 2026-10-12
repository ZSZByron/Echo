# -*- coding: utf-8 -*-
"""批D（波次二）：灵感架三回收时机 + 入架路径 + 埋点收口 + 门禁不阻塞。

设计依据：docs/plans/2026-10-10-结构接住想象-投递式访谈机制设计.md §2.3。
- 入架：投递「无家可归」素材 → rack_stowed 话术（含「灵感架」）+ pool +1
  + rack_stowed 事件——永不拒绝（帽满挤最旧，不拒收）。
- 回收时机①自由流程：pool 有存量 → 正常答题轮后安家提议（复用 D23
  resolve_proposal 拍板）→ 确认 → 目标 L3 落写 + pool -1 + rack_recycled
  事件 1 条；拒绝 → pool 保留、事件 0。**用户确认铁律**：引擎只提议，
  LLM 绝不直写。
- 回收时机②收尾盘点：closing 预览摊开 pool 存量（预览文本含条目）；
  pool 非空不阻塞 finalize（跨定稿存档）。
- 埋点收口：rack_stowed / rack_recycled / list_append 三事件 jsonl
  （与批C 同文件 additive、fail-silent、tmp_path 重定向）。
- 数据面预留：/file/{file_id} GET 响应含 material_pool。
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domains.creation.a1 import inspiration_log
from app.domains.creation.a1.closing_flow import maybe_trigger
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_COMPLETED,
    handle_message,
    resolve_proposal,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
)


# ---------------------------------------------------------------------------
# harness（照 test_inspiration_log / test_delivery_intent 先例）
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_log_path(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    log_path = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", log_path)
    return log_path


def _events(log_path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(ln)
        for ln in log_path.read_text(encoding="utf-8").splitlines()
    ]


def _rack_events(log_path) -> list[dict]:
    """批D 三事件过滤视图（排除无关的 stall/skip 等既有遥测）。"""
    return [
        e for e in _events(log_path)
        if e.get("event") in {"rack_stowed", "rack_recycled", "list_append"}
    ]


def make_session() -> A1Session:
    return A1Session(session_id="s_rack", user_id="u1", ip_code="IP0001")


class _DeliveryStub:
    """delivery=true 且无 fills 的投递轮（无家可归 → 灵感架）。

    suggested_slots 走 model_construct 注入（test_channel_matrix_v2 先例：
    引擎侧 getattr 发现式消费——schema 键集冻结锁零扩容）。
    """

    def __init__(self, slots: list[str] | None = None):
        self._slots = slots or []

    def interview(self, session, text):  # noqa: ARG002
        result = InterviewResult.model_construct(
            fills=[],
            guidance_reply="这个画面真好。",
            delivery=True,
        )
        # 非字段属性注入（pydantic v2 model_construct 不收未知键）
        result.__dict__["suggested_slots"] = list(self._slots)
        return result

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


class _NormalFillStub:
    """正常答题轮（自由流程回收时机的触发载体）。"""

    def interview(self, session, text):  # noqa: ARG002
        return InterviewResult(
            fills=[InterviewFill(
                module="力量体系", subfield="acquire", value="古神遗骸",
            )],
            guidance_reply="已记录。",
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _rack_item(text: str, slots: list[str]) -> dict[str, Any]:
    return {"text": text, "suggested_slots": list(slots), "created_at": "t0"}


# ---------------------------------------------------------------------------
# 1. 入架路径：投递无家可归素材 → rack_stowed
# ---------------------------------------------------------------------------


class TestRackStowed:
    def test_delivery_no_home_stows_into_pool(self, tmp_log_path):
        s = make_session()
        iv = _DeliveryStub(slots=["视觉.标志性意象", "世界起源"])
        out = handle_message(s, "我总想象一个画面：满天都是断掉的剑。", iv)
        # pool +1：条目 = {原文, 建议槽位, ...}
        assert len(s.material_pool) == 1
        entry = s.material_pool[0]
        assert "断掉的剑" in entry["text"]
        assert "视觉.标志性意象" in entry["suggested_slots"]
        # rack_stowed 话术：含「灵感架」，永不拒绝
        assert "灵感架" in out["reply"]
        # rack_stowed 事件 1 条
        evs = _rack_events(tmp_log_path)
        assert [e["event"] for e in evs].count("rack_stowed") == 1

    def test_stow_never_rejects_cap_overflow_drops_oldest(
        self, tmp_log_path, monkeypatch
    ):
        from app.domains.creation.seed.story_modules import LIST_CAPS

        s = make_session()
        s.material_pool = [
            _rack_item(f"旧素材{i:02d}", ["世界起源"]) for i in range(
                LIST_CAPS["material_pool"]
            )
        ]
        iv = _DeliveryStub(slots=["世界起源"])
        out = handle_message(s, "雨夜码头", iv)
        # 永不拒绝：帽满挤最旧，新条目入架
        assert len(s.material_pool) == LIST_CAPS["material_pool"]
        assert s.material_pool[-1]["text"] == "雨夜码头"
        assert s.material_pool[0]["text"] == "旧素材01"
        assert "灵感架" in out["reply"]

    def test_delivery_with_fills_not_stowed(self, tmp_log_path):
        # delivery=true 但 fills 非空 = 归位（落既有槽），不入架。
        s = make_session()

        class _HomeDelivery:
            def interview(self, session, text):  # noqa: ARG002
                return InterviewResult(
                    fills=[InterviewFill(
                        module="IP定位", subfield="concept",
                        value="师姐的剑挂在城门口",
                    )],
                    guidance_reply="记进【支线卡·结局】了。",
                    delivery=True,
                )

            def suggest_examples(self, session, m, sf):  # noqa: ARG002
                return []

        handle_message(s, "对了！主角最后把师姐的剑挂在城门口了。", _HomeDelivery())
        assert s.material_pool == []
        assert _rack_events(tmp_log_path) == []


# ---------------------------------------------------------------------------
# 2. 回收时机①自由流程：安家提议 → 用户确认（LLM 只提议）
# ---------------------------------------------------------------------------


class TestFreeFlowRecycle:
    def _session_with_pool(self) -> A1Session:
        s = make_session()
        s.material_pool = [_rack_item("满天断剑", ["视觉.标志性意象"])]
        return s

    def test_fill_turn_proposes_homing_with_target_slot(self, tmp_log_path):
        s = self._session_with_pool()
        out = handle_message(s, "力量来自古神遗骸", _NormalFillStub())
        # 自由流程正常答题轮后：安家提议（含目标 L3 槽位 + 原文）
        assert "断剑" in out["reply"]
        assert "标志性意象" in out["reply"]
        assert "安进去" in out["reply"]
        # 提议已挂起（pending，走 resolve_proposal 拍板）
        assert len(s.pending_proposals) == 1
        # pool 未动、answers 未动（用户确认铁律：LLM 只提议）
        assert len(s.material_pool) == 1
        assert "力量体系.acquire" in s.answers  # 本轮正常 fill 照常落
        assert _rack_events(tmp_log_path) == []      # 未确认前零事件

    def test_confirm_homes_item_pool_minus_one_event_one(self, tmp_log_path):
        s = self._session_with_pool()
        handle_message(s, "力量来自古神遗骸", _NormalFillStub())
        key = next(k for k in s.pending_proposals if k.startswith("rack_home:"))
        # 用户确认「安进去」→ resolve_proposal replace
        result = resolve_proposal(s, key, "replace")
        assert result["applied"] is True
        # 目标 L3 落写（树内锚键 = L2 id「视觉」，子节点 source=标志性意象）
        assert len(s.material_pool) == 0          # pool -1
        evs = _rack_events(tmp_log_path)
        assert [e["event"] for e in evs].count("rack_recycled") == 1
        rec = next(e for e in evs if e["event"] == "rack_recycled")
        assert rec["target"] == "视觉.标志性意象"

    def test_reject_keeps_pool_zero_events(self, tmp_log_path):
        s = self._session_with_pool()
        handle_message(s, "力量来自古神遗骸", _NormalFillStub())
        key = next(k for k in s.pending_proposals if k.startswith("rack_home:"))
        result = resolve_proposal(s, key, "drop")
        assert result["applied"] is False
        assert len(s.material_pool) == 1          # pool 保留
        assert _rack_events(tmp_log_path) == []        # 事件 0
        # 拒绝后不再重复提议（下轮正常答题不弹同一条）
        out = handle_message(s, "力量来自血祭", _NormalFillStub())
        assert "断剑" not in out["reply"]

    def test_engine_confirm_hook_answert_phrases(self, tmp_log_path):
        # 引擎侧确定性确认钩子：显式短语「安进去」/「先留着」
        s = self._session_with_pool()
        handle_message(s, "力量来自古神遗骸", _NormalFillStub())
        out = handle_message(s, "安进去", _NormalFillStub())
        assert len(s.material_pool) == 0
        assert "安家" in out["reply"]
        evs = _rack_events(tmp_log_path)
        assert [e["event"] for e in evs].count("rack_recycled") == 1


# ---------------------------------------------------------------------------
# 3. 回收时机②收尾盘点：closing 预览摊开 pool 存量
# ---------------------------------------------------------------------------


class TestClosingInventory:
    def _completed_session_with_pool(self) -> A1Session:
        s = make_session()
        s.phase = PHASE_COMPLETED
        s.material_pool = [
            _rack_item("满天断剑", ["视觉.标志性意象"]),
            _rack_item("雨夜码头", ["世界起源"]),
        ]
        return s

    def test_closing_trigger_previews_pool_items(self):
        s = self._completed_session_with_pool()
        prompt = maybe_trigger(s)
        assert prompt is not None
        assert "灵感架" in prompt
        assert "满天断剑" in prompt                 # 预览摊开条目
        assert "雨夜码头" in prompt

    def test_closing_without_pool_no_inventory_line(self):
        s = make_session()
        s.phase = PHASE_COMPLETED
        prompt = maybe_trigger(s)
        assert prompt is not None
        assert "灵感架" not in prompt               # 空架不盘点


# ---------------------------------------------------------------------------
# 4. 门禁不阻塞：pool 非空 → finalize 200（跨定稿存档）
# ---------------------------------------------------------------------------


class TestGateUnblocked:
    @pytest.fixture()
    def started(self):
        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u_rack", "seed_id": 1},
        )
        assert resp.status_code == 200
        return client, resp.json()

    def test_finalize_200_with_pool_not_in_missing(self, started):
        from app.api import a1_routes
        from app.domains.creation.seed.a1_question_tree import all_subfield_keys

        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        for key in all_subfield_keys():
            session.answers[key] = f"答案-{key}"
        session.material_pool = [
            _rack_item("满天断剑", ["视觉.标志性意象"]),
            _rack_item("雨夜码头", ["世界起源"]),
        ]
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200               # pool 不阻塞门禁
        body = fin.json()
        assert "material_pool" not in (body.get("missing_sections") or [])
        # 跨定稿存档：finalize 后 /file 仍可读 pool（数据面预留）
        f = client.get(f"/api/a1/file/{payload['file_id']}")
        assert f.status_code == 200
        assert "material_pool" in f.json()
        assert len(f.json()["material_pool"]) == 2

    def test_get_file_material_pool_key_in_draft(self, started):
        client, payload = started
        f = client.get(f"/api/a1/file/{payload['file_id']}")
        assert f.status_code == 200
        assert f.json()["material_pool"] == []


# ---------------------------------------------------------------------------
# 5. 埋点收口：list_append 事件（清单条目追加）
# ---------------------------------------------------------------------------


class TestListAppendEvent:
    def test_list_complement_emits_list_append(self, tmp_log_path):
        from app.domains.creation.a1.guide_engine import _apply_fills

        s = make_session()
        fills = [InterviewFill(
            module="文明与社会", subfield="conflict", value="教廷与王权",
            relation="complement",
        )]
        _apply_fills(s, fills)
        evs = _rack_events(tmp_log_path)
        assert [e["event"] for e in evs].count("list_append") == 1
        rec = next(e for e in evs if e["event"] == "list_append")
        assert rec["subfield"] == "conflict"

    def test_plain_fill_no_list_append(self, tmp_log_path):
        from app.domains.creation.a1.guide_engine import _apply_fills

        s = make_session()
        fills = [InterviewFill(
            module="力量体系", subfield="acquire", value="古神遗骸",
        )]
        _apply_fills(s, fills)
        assert _rack_events(tmp_log_path) == []
