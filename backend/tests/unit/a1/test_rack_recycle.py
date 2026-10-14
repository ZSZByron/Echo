"""批D（T8）红测：灵感架三回收时机引擎侧 + 五事件埋点收口。

三回收时机（设计原文 §③，docs/plans/2026-10-10-结构接住想象-投递式访谈
机制设计.md）：
- 时机一：自由流程提议——预设配方完成（is_preset_phase_complete）时
  material_pool 有存量 → 引擎生成「安家提议」（复用 resolve_proposal
  提议流先例：pending_proposals 装包，用户 confirm 后写入对应 L3 清单/
  字段并从 pool 移除；拒绝（drop）则 pool 保留）。
- 时机二：收尾盘点摊开——closing_gate 收尾三连问触发环节，预览摊开
  pool 存量（「你还有 N 个想法在灵感架上：…，要安家吗？」）；不安家
  随定稿存档（pool 不清空、跨定稿保留）。
- 时机三：图谱页安放——本批零实现（数据面 material_pool 随会话持久化
  已就绪，/file/{id} 状态可读；UI 归波次三）。

入架路径：投递通道判定「无家可归」（delivery=true 且无槽可落 = fills
空）→ rack_stowed 话术 + pool append（永不拒收）。通道全序（批C）不变：
rack 入架发生在投递分支内部（镜像之后、答当前之前）。

埋点（事件名逐字锁）：rack_stowed / rack_recycled / list_append 落
backend/data/inspiration_log.jsonl（fail-silent，与批C
mirror_triggered/reanchor_triggered 同机制）。

门禁不阻塞：pool 有存量不进 missing_sections、不阻塞 finalize。

TDD 纪律：先 RED（断言失败非语法错误）后 GREEN。
全部引擎级（A1Session + handle_message + stub interviewer）。
"""
from __future__ import annotations

import pytest

from app.domains.creation.a1 import inspiration_log
from app.domains.creation.a1.closing_gate import is_preset_phase_complete
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_COMPLETED,
    core_recipe_modules,
    handle_message,
    resolve_proposal,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
)
from app.domains.creation.seed.a1_question_tree import (
    get_subfield,
    is_module_over_half,
)

# ---------------------------------------------------------------------------
# stub / 工具（形状照 test_channel_matrix_v2.py 既有约定）
# ---------------------------------------------------------------------------


class _Stub:
    """handle_message 级 stub：可控 delivery / fills（批C stub 同形）。"""

    def __init__(
        self,
        *,
        delivery: bool = False,
        knowledge_used: bool = False,
        fills: list[InterviewFill] | None = None,
        guidance_reply: str = "好的，继续",
    ):
        self.delivery = delivery
        self.knowledge_used = knowledge_used
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            knowledge_used=self.knowledge_used,
            delivery=self.delivery,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _capture_events(monkeypatch: pytest.MonkeyPatch) -> list:
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        inspiration_log,
        "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    return events


def _event_names(events: list) -> list[str]:
    return [name for name, _fields in events]


def _session(**kw) -> A1Session:
    base = dict(
        session_id="s_rack",
        user_id="u1",
        current_module="IP定位",
        current_subfield="name",
    )
    base.update(kw)
    return A1Session(**base)


def _rack_item(text: str, home: str = "IP定位.name") -> dict:
    return {"text": text, "home": home, "turn": 1}


# ---------------------------------------------------------------------------
# 入架路径：投递无家 → rack_stowed 话术 + pool append（永不拒收）
# ---------------------------------------------------------------------------


class TestRackStow:
    def test_delivery_no_home_stows_to_pool(self, monkeypatch):
        events = _capture_events(monkeypatch)
        s = _session()
        out = handle_message(
            s, "我总想象一个画面：满天都是断掉的剑。", _Stub(delivery=True)
        )
        assert len(s.material_pool) == 1                    # 永不拒收：pool +1
        assert s.material_pool[0]["text"].startswith("我总想象")
        assert "灵感架" in out["reply"]                     # rack_stowed 话术
        assert out["next_question"] is not None             # 回题（不问两遍）
        assert s.answers == {}                              # 不占当前题槽
        assert "rack_stowed" in _event_names(events)        # 埋点落盘契约

    def test_delivery_with_fills_does_not_stow(self, monkeypatch):
        events = _capture_events(monkeypatch)
        s = _session()
        handle_message(
            s,
            "对了！结局画面是剑挂城门口",
            _Stub(
                delivery=True,
                fills=[InterviewFill(
                    module="IP定位", subfield="concept", value="剑挂城门口",
                )],
            ),
        )
        assert s.material_pool == []                        # 有槽可落 → 不入架
        assert s.answers.get("IP定位.concept") == "剑挂城门口"
        assert "rack_stowed" not in _event_names(events)

    def test_stow_event_lands_jsonl(self, tmp_path, monkeypatch):
        # 埋点落盘契约：rack_stowed 真实写 backend/data/inspiration_log.jsonl
        # 机制（LOG_PATH 指到 tmp 隔离；emit_event 本体 fail-silent 已由
        # test_inspiration_log.py 锁定）。
        log_path = tmp_path / "inspiration_log.jsonl"
        monkeypatch.setattr(inspiration_log, "LOG_PATH", log_path)
        s = _session()
        handle_message(s, "满天断剑", _Stub(delivery=True))
        import json

        lines = log_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(ln) for ln in lines]
        assert any(r["event"] == "rack_stowed" for r in records)


# ---------------------------------------------------------------------------
# 回收时机一：自由流程提议（复用 resolve_proposal 提议流先例）
# ---------------------------------------------------------------------------


class TestRackRecycleProposal:
    def _completed_session_with_pool(self) -> A1Session:
        s = _session(phase=PHASE_COMPLETED)
        # home 选 L3 清单位点（角色.key_relations = multi 清单）——
        # 安家落槽 = 清单追加；单值字段走 resolve_proposal 既有 merge 串接。
        s.material_pool.append(
            _rack_item("师姐的剑挂在城门口", home="角色.key_relations")
        )
        return s

    def test_free_flow_proposes_rack_home(self, monkeypatch):
        events = _capture_events(monkeypatch)
        s = self._completed_session_with_pool()
        assert is_preset_phase_complete(s)
        out = handle_message(s, "再补充一点设定", _Stub())
        assert "安" in out["reply"]                         # 安家提议话术
        rack_keys = [k for k in s.pending_proposals if k.startswith("rack:")]
        assert rack_keys, f"pending_proposals={list(s.pending_proposals)}"
        assert s.material_pool[0].get("proposed") is True   # 提议去重标记
        assert "rack_recycled" not in _event_names(events)  # 确认前不回收

    def test_confirm_recycles_into_l3_list_and_pops_pool(self, monkeypatch):
        events = _capture_events(monkeypatch)
        s = self._completed_session_with_pool()
        handle_message(s, "再补充一点设定", _Stub())
        rack_keys = [k for k in s.pending_proposals if k.startswith("rack:")]
        result = resolve_proposal(s, rack_keys[0], "merge")  # 安家 = 并入清单
        assert result["applied"] is True
        assert s.material_pool == []                        # 确认后从 pool 移除
        node = s.answers["角色.key_relations"]
        children_texts = [c.text for c in getattr(node, "children", [])]
        assert "师姐的剑挂在城门口" in children_texts       # L3 清单 +1
        assert "rack_recycled" in _event_names(events)      # 回收埋点

    def test_reject_keeps_pool(self, monkeypatch):
        events = _capture_events(monkeypatch)
        s = self._completed_session_with_pool()
        handle_message(s, "再补充一点设定", _Stub())
        rack_keys = [k for k in s.pending_proposals if k.startswith("rack:")]
        result = resolve_proposal(s, rack_keys[0], "drop")  # 拒绝
        assert result["applied"] is False
        assert len(s.material_pool) == 1                    # 拒绝 → pool 保留
        assert "rack_recycled" not in _event_names(events)

    def test_no_repropose_for_already_proposed_item(self):
        s = self._completed_session_with_pool()
        handle_message(s, "再补充一点设定", _Stub())
        rack_keys = [k for k in s.pending_proposals if k.startswith("rack:")]
        resolve_proposal(s, rack_keys[0], "drop")
        s.pending_proposals.clear()
        handle_message(s, "再补充一点设定", _Stub())        # 第二轮
        rack_keys2 = [k for k in s.pending_proposals if k.startswith("rack:")]
        assert rack_keys2 == []                             # 已提议过 → 不重复 nag


# ---------------------------------------------------------------------------
# 回收时机二：closing_gate 收尾触发环节预览摊开 pool 存量
# ---------------------------------------------------------------------------


class TestClosingPreview:
    def test_closing_trigger_spreads_pool(self):
        s = _session(phase=PHASE_COMPLETED)
        s.material_pool.append(_rack_item("断剑满天"))
        s.material_pool.append(
            _rack_item("钟表铺里的暗门", home="IP定位.concept")
        )
        out = handle_message(s, "继续", _Stub())
        assert s.closing_step == 1                          # 收尾已触发
        assert "2 个想法在灵感架上" in out["reply"]          # 摊开预览
        assert "断剑满天" in out["reply"]
        assert "要安家吗" in out["reply"]
        assert len(s.material_pool) == 2                    # pool 不清空
        assert "定稿" in out["reply"]                       # 存档告知

    def test_no_preview_when_pool_empty(self):
        s = _session(phase=PHASE_COMPLETED)
        out = handle_message(s, "继续", _Stub())
        assert s.closing_step == 1
        assert "灵感架上" not in out["reply"]

    def test_pool_survives_closing_settled(self):
        s = _session(phase=PHASE_COMPLETED)
        s.material_pool.append(_rack_item("断剑满天"))
        s.closing_step = 3
        handle_message(s, "就到这", _Stub())
        assert s.closing_settled is True
        assert len(s.material_pool) == 1                    # 跨定稿保留（存档）


# ---------------------------------------------------------------------------
# 门禁不阻塞：pool 非空不进 missing_sections、finalizable 不受影响
# ---------------------------------------------------------------------------


class TestGateUnblocked:
    def _full_answers_session_with_pool(self) -> A1Session:
        s = _session(recipe_modules=["IP定位"])
        for sf_id in ("name", "concept", "world_type", "core_experience"):
            s.answers[f"IP定位.{sf_id}"] = f"值-{sf_id}"
        s.material_pool.append(_rack_item("断剑满天"))
        s.material_pool.append(_rack_item("钟表铺里的暗门"))
        return s

    def test_missing_sections_excludes_pool(self):
        s = self._full_answers_session_with_pool()
        missing = [
            mid for mid in core_recipe_modules(s)
            if not is_module_over_half(mid, s.answers)
        ]
        assert missing == []                                # pool 不进门禁

    def test_finalizable_with_pool(self):
        s = self._full_answers_session_with_pool()
        from app.domains.creation.a1.guide_engine import progress

        assert progress(s)["finalizable"] is True
        assert get_subfield("IP定位", "name") is not None   # 字段宇宙在位


# ---------------------------------------------------------------------------
# 回收时机三：图谱页安放——零实现声明（数据面已就绪、UI 归波次三）
# ---------------------------------------------------------------------------


def test_timing_three_graph_page_out_of_scope_declaration():
    """回收时机三（图谱页安放）本批零实现：material_pool 数据面随会话
    持久化已就绪（批A 落库），/file/{id} 状态可读；UI 归波次三。"""
    s = _session()
    s.material_pool.append(_rack_item("断剑满天"))
    assert s.material_pool[0]["text"] == "断剑满天"         # 数据面在位
