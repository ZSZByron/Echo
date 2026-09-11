"""E2 极限实验 · 门禁与答案炸弹。

打击面（用户投票定案 #8/#6）：
  #8  门禁只查 key 存在 —— "跳过"写空串（guide_engine.py:505 setdefault("","")）、
      占位值"缺少依据"统统过 50% 门禁 —— 看不见的放行
  #6  答案无长度护栏 —— 35 字段 × 5000 字全文嵌入 graphify prompt（C1 契约
      verbatim 无截断）—— 超时降级后 finalize 仍报"成功"

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
    """#8 占位值木马：语义为空的答案照样过定稿门禁。"""

    def test_unit_placeholder_values_pass_gate(self):
        answers = dict.fromkeys(all_subfield_keys(), "缺少依据")
        # BUG(#8a): is_module_over_half 只检查 key 是否存在，不检查语义内容 ——
        # 全字段"缺少依据"的会话可以合法定稿
        assert is_finalizable(answers) is True

    def test_unit_skip_empty_strings_pass_gate(self):
        answers = dict.fromkeys(all_subfield_keys(), "")
        # BUG(#8b): guide_engine「跳过」分支写入的就是空字符串（setdefault(key,"")），
        # 空串 key 同样计入 >50% 门禁 —— 存量测试 _fill_all_subs 正是靠这个过的门
        assert is_finalizable(answers) is True

    @pytest.mark.usefixtures("no_visual_bg")
    def test_route_placeholder_finalize_still_200(self, started, monkeypatch):
        client, payload = started
        inject_answers(
            payload["session_id"], dict.fromkeys(all_subfield_keys(), "缺少依据")
        )

        def _boom(*_a, **_k):
            raise RuntimeError("no llm for xt")

        monkeypatch.setattr(a1_routes, "create_provider", _boom)
        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        # BUG(#8+#6 双重放行): 占位值过门禁（无 409）+ LLM 失败降级后照样定稿成功
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "finalized"
        # 降级契约生效的部分：warning 落响应且落库（这部分是设计行为，不算 bug）
        assert body["warnings"]
        rec = a1_routes._FILES[payload["file_id"]]
        assert rec["finalize_warnings"]
        assert rec["status"] == "finalized"


class TestE21AnswerBomb:
    """#6 答案炸弹：35×5000 字答案全文进 graphify prompt，无任何护栏。"""

    @pytest.mark.usefixtures("no_visual_bg")
    def test_graphify_prompt_exceeds_100k_chars(self, started, monkeypatch):
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
        # BUG(#6): 35 字段 × ~5000 字 = 17.5 万字全文嵌入（C1 verbatim 契约 + 全链路
        # 无长度护栏）。Mock 下不超时；真跑将吃满 2×120s 预算后降级 —— 而降级仍定稿成功
        assert len(system_prompt) > 100_000
        assert resp.json()["status"] == "finalized"
