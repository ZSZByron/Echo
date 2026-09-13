"""E1 极限实验 · 输入病理学。

打击面（用户投票定案 #2/#3/#4）：
  #2  20000 字符硬截断 —— 后半设定对解析永不可见；响应仅弱披露布尔
      → J3/J4 后已补强：upload 落 ledger（响应布尔仍在）；截断线本身
        是钦定预算，属设计取舍（非 bug）
  #3  convert_text 唯一不截断入口 —— 全文直灌 prompt
      → J4 已修复（2026-09-11）：输入 ≤20000 + prompt 留痕，TestE17 已翻转
  #4  专有名词每类 cap=10 —— 第 11 个起静默丢弃且无披露
      → J4 已修复（2026-09-11）：capped 披露 + 上传落 ledger，TestE15 已翻转

判据：B（看不见的丢失）。确诊条件 = 数据缺失且无警告落库/响应。
"""
from __future__ import annotations

import asyncio

import pytest

from app.api import a1_routes
from app.domains.creation.a1.worldview_upload import (
    convert_text,
    extract_entities,
    parse_modules,
)
from tests.xt.helpers import FakeProvider, dual_sentinel_doc

pytestmark = pytest.mark.xt


class TestE14TruncationBlindSpot:
    """#2 截断失忆症：哨兵 B 只存在于 20000 字之后。"""

    def test_sentinel_beyond_20k_never_reaches_llm(self):
        doc = dual_sentinel_doc()
        fake = FakeProvider({"answers": {}, "innovations": []})
        result = asyncio.run(parse_modules(fake, doc))

        user_msg = fake.calls[0][1]["content"]
        # 头部哨兵可见（管线正常部分的对照）
        assert "星陨大陆" in user_msg
        # BUG(#2): 20000 字之后的设定对 parse_modules 永不可见 —— 内容层静默丢失，
        # truncated 布尔不指明丢了哪些字段，也没有任何逐字段补捞机制
        assert "玄骸纹章" not in user_msg
        assert result["truncated"] is True

    @pytest.mark.usefixtures("no_visual_bg")
    def test_upload_response_only_weak_disclosure(self, client, monkeypatch):
        """路由层：响应确实携带 truncated 布尔（弱披露存在），但仅此而已。"""
        doc = dual_sentinel_doc()

        def route_payload(messages):
            system = messages[0]["content"]
            if "版权风险分析助手" in system:
                return {
                    "characters": ["主角甲"],
                    "power_systems": [],
                    "world_keywords": [],
                    "suspected_works": [],
                }
            if "版权合规审核员" in system:
                return {"risk_level": "low", "matches": []}
            return {"answers": {"IP定位.name": "星陨界"}, "innovations": []}

        fake = FakeProvider(route_payload)
        monkeypatch.setattr(a1_routes, "_get_upload_provider", lambda: fake)

        resp = client.post(
            "/api/a1/upload",
            json={"user_id": "u_xt_e14", "filename": "长文.txt", "content": doc},
        )
        assert resp.status_code == 200
        body = resp.json()
        # 弱披露：布尔在响应里（后端尽责）；"玄骸纹章"所属字段不可能被预填
        assert body["truncated"] is True
        assert "视觉设计.keywords" not in body["file"]["answers"]


class TestE15NounCapSilentDrop:
    """#4 专名洪水：每类 cap=10，第 11 个起静默丢弃。

    J4 已落地（2026-09-11）：capped 报告每类丢弃数（配 J3 披露落
    warning ledger）——断言翻转为期望行为。
    """

    def test_cap_drops_20_nouns_with_disclosure(self):
        thirty_names = [f"重要角色{chr(0x4E00 + i)}号" for i in range(30)]
        fake = FakeProvider(
            {
                "characters": thirty_names,
                "power_systems": [],
                "world_keywords": [],
                "suspected_works": [],
            }
        )
        result = asyncio.run(extract_entities(fake, "任意超过两百字的设定文本。" * 20))

        # cap 是确定性生效的：30 → 10
        assert len(result["characters"]) == 10
        # J4 fixed(#4): 被丢弃的 20 个专名有 capped 披露字段（版权审查
        # 失明范围可见——上传路由将其落 warning ledger，source=upload）
        assert result["capped"] == {"characters": 20}


class TestE17ConvertFullTextBomb:
    """#3 convert 炸弹：唯一不做截断的全文入口。

    J4 已落地（2026-09-11）：输入 ≤20000 + prompt 内截断留痕标记
    ——断言翻转为期望行为。
    """

    def test_convert_input_truncated_with_marker(self):
        doc = "灵石大陆以灵石为本位货币，修行者以灵养魔躯壳。" * 5500  # 约104k 字符
        fake = FakeProvider({"converted": "净化后的全文"})
        out = asyncio.run(
            convert_text(
                fake,
                doc,
                [{"term": "灵石大陆", "work": "灵石大陆体系", "evidence": "同名"}],
            )
        )
        user_msg = fake.calls[0][1]["content"]
        # J4 fixed(#3): convert 不再全文直灌（曾 10 万字文档全文进 user
        # prompt → token 爆炸/400/秒杀预算）；截断至 20000 + 留痕标记
        assert len(user_msg) < 21_000
        assert "已截断" in user_msg
        assert out == "净化后的全文"
