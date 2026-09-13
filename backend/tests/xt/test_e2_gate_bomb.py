"""E2 极限实验 · 门禁与答案炸弹。

打击面（用户投票定案 #8/#6）：
  #8  门禁只查 key 存在 —— "跳过"写空串（guide_engine.py setdefault("","")）、
      占位值"缺少依据"统统过 50% 门禁 —— 看不见的放行
      → J1 已修复（2026-09-11，2-A1-v0.5.1 §3）：TestE22 断言已翻转为期望行为；
        残余风险=词典漏新变体，由 J3 披露协议兜底
  #6  答案无长度护栏 —— 35 字段 × 5000 字全文嵌入 graphify prompt（C1 契约
      verbatim 无截断）—— 超时降级后 finalize 仍报"成功"
      → J4 已修复（2026-09-11，2-A1-v0.5.1 §3）：TestE21 断言已翻转为期望
        行为（prompt 预算钳制 + [budget] 披露进 ledger）

判据：C（看不见的放行）。
"""
from __future__ import annotations

import pytest

from app.api import a1_routes
from app.domains.creation.seed.a1_question_tree import all_subfield_keys, is_finalizable
from tests.xt.conftest import full_answers, inject_answers
from tests.xt.helpers import ANCHOR, FakeProvider, canned_graphify

pytestmark = pytest.mark.xt


class TestE22PlaceholderGate:
    """#8 占位值木马：语义为空的答案照样过定稿门禁。

    J1 已落地（2-A1-v0.5.1 §3）：断言翻转为期望行为——
    占位值/空串不计入门禁分子，is_finalizable 为 False，路由 409。
    """

    def test_unit_placeholder_values_blocked_by_gate(self):
        answers = dict.fromkeys(all_subfield_keys(), "缺少依据")
        # J1 fixed(#8a): 门禁计数真值感知（module_done_ratio 只数真值）
        assert is_finalizable(answers) is False

    def test_unit_skip_empty_strings_blocked_by_gate(self):
        answers = dict.fromkeys(all_subfield_keys(), "")
        # J1 fixed(#8b): 空串（guide_engine「跳过」分支 setdefault(key,"") 的
        # 存量/直注数据）同样不计入门禁 —— 跳过 UX 不变，但无法借此定稿
        assert is_finalizable(answers) is False

    @pytest.mark.usefixtures("no_visual_bg")
    def test_route_placeholder_finalize_409(self, started, monkeypatch):
        client, payload = started
        inject_answers(
            payload["session_id"], dict.fromkeys(all_subfield_keys(), "缺少依据")
        )

        def _boom(*_a, **_k):
            raise RuntimeError("no llm for xt")

        monkeypatch.setattr(a1_routes, "create_provider", _boom)
        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        # J1 fixed(#8): 占位值过不了 50% 门禁 → 409 + missing_sections，
        # graphify（含其降级契约）根本不会被触发
        assert resp.status_code == 409
        assert resp.json()["detail"]["missing_sections"]


class TestE21AnswerBomb:
    """#6 答案炸弹：35×5000 字答案全文进 graphify prompt，无任何护栏。

    J4 已落地（2026-09-11，2-A1-v0.5.1 §3）：断言翻转为期望行为——
    prompt 被预算钳制（每答案 2000 + 答案块总长 60000）+ 截断披露进
    warning ledger（source=graphify，[budget] 前缀）。
    """

    @pytest.mark.usefixtures("no_visual_bg")
    def test_graphify_prompt_budget_bounded_and_disclosed(self, started, monkeypatch):
        client, payload = started
        # 每字段 5000 字（用户在访谈里粘贴长文即可达成，无长度校验拦截）
        inject_answers(
            payload["session_id"], full_answers(lambda _k: "灵气复苏的叙事纹理。" * 357)
        )
        fake = FakeProvider(
            canned_graphify(
                entries=[
                    {
                        "anchor": ANCHOR,
                        "items": [{"title": "斗气分裂", "content": "条目内容"}],
                    }
                ]
            )
        )
        monkeypatch.setattr(
            a1_routes, "create_provider", lambda *_a, **_k: fake
        )

        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert resp.status_code == 200

        system_prompt = fake.calls[0][0]["content"]
        # J4 fixed(#6): 每答案 ≤2000 + 答案块 ≤60000 → 总 prompt 远低于
        # 旧病理的 17.5 万字（真跑曾吃满 2×120s 预算后降级）
        assert len(system_prompt) < 100_000
        for line in system_prompt.splitlines():
            if " = " in line:
                _k, _, v = line.partition(" = ")
                assert len(v) <= 2000
        # 截断有痕：预算披露进 ledger（[budget] 前缀，source=graphify）
        rec = a1_routes._FILES[payload["file_id"]]
        budget_entries = [
            e for e in rec["warnings"]
            if e["source"] == "graphify" and "[budget]" in e["detail"]
        ]
        assert budget_entries
        assert all(e["level"] == "warn" for e in budget_entries)
        assert resp.json()["status"] == "finalized"
