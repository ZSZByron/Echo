"""人格卡（persona card）+ 入口单选 sunset 接口契约测试（M4c，plan §276-284）。

人格卡契约：
- 命名 = 未决③ DECISION NEEDED 占位 "ECHO 创作人格"（占位常量，终名归产品裁决）；
- 数据源 = creator_profile（creator_primary / creator_profile_source）+
  impulse_coords 三件套（M4b）——数据源断言（改档案/坐标 → 卡面随之变化）；
- 确定性投影：同输入 → 同卡面（零 LLM，纯函数）；
- 只看不判：渲染不改写会话观察数据（answers 不动 / 坐标仅惰性初始化，
  不产生新审计/重排——与 dashboard_data 同款只读投影惯例）。

sunset 契约（plan §281）：行为信号（坐标置信度）成熟后选卡权重递减——
**本期只留接口不启用**：默认（环境变量未开）恒返回基础权重，行为零变化。
"""
from typing import Any

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.impulse_coords import (
    apply_signal,
    init_impulse_coords,
)
from app.domains.creation.a1.persona_card import (
    PERSONA_NAME_PLACEHOLDER,
    entry_card_weight,
    render_persona_card,
)


def make_session(**kw: Any) -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001", **kw)


class TestPersonaCardNaming:
    """未决③ 占位命名锁定——终名归产品裁决，不得擅定。"""

    def test_name_is_placeholder_pending_decision_3(self):
        # 未决③ DECISION NEEDED：默认占位，G 批次在 D14/spec 记录状态
        assert PERSONA_NAME_PLACEHOLDER == "ECHO 创作人格"

    def test_card_carries_placeholder_name(self):
        card = render_persona_card(make_session(creator_primary="plot"))
        assert card["name"] == "ECHO 创作人格"


class TestPersonaCardDeterministic:
    """确定性投影：同输入 → 同卡面；零 LLM（纯函数，无 provider 依赖）。"""

    def test_same_input_same_card(self):
        cards = [
            render_persona_card(make_session(creator_primary="romance"))
            for _ in range(2)
        ]
        assert cards[0] == cards[1]

    def test_card_shape(self):
        card = render_persona_card(make_session())
        # 渲染三件：命名 + 视觉 + 一句话解读
        assert set(card) >= {"name", "visual", "one_line_reading"}
        assert isinstance(card["visual"], dict)
        assert isinstance(card["one_line_reading"], str)
        assert card["one_line_reading"]


class TestPersonaCardDataSource:
    """数据源断言：creator_profile + impulse_coords 共同喂卡。"""

    def test_sources_field_records_provenance(self):
        s = make_session(creator_primary="plot", creator_profile_source="impulse_cards")
        init_impulse_coords(s)
        card = render_persona_card(s)
        src = card["sources"]
        assert src["creator_primary"] == "plot"
        assert src["creator_profile_source"] == "impulse_cards"
        assert src["axis"] == 70  # plot 锚点（spec L309）
        assert 0.0 <= src["confidence"] <= 1.0
        assert src["safety_flag"] is False

    def test_profile_change_changes_card(self):
        # creator_profile 档案变化 → 锚点随查表变化（数据源因果）
        a = render_persona_card(make_session(creator_primary="healing"))
        b = render_persona_card(make_session(creator_primary="setting_heavy"))
        assert a["sources"]["axis"] == 85
        assert b["sources"]["axis"] == 15
        assert a != b

    def test_coord_signal_changes_card(self):
        # 显式信号 → 坐标更新 → 卡面随之变化（M4b 坐标喂卡）
        s1 = make_session(creator_primary="plot")
        s2 = make_session(creator_primary="plot")
        init_impulse_coords(s2)
        apply_signal(s2, "fill_confirmed", key="剧情.core_dilemma")
        assert render_persona_card(s1) != render_persona_card(s2)


class TestPersonaCardObserveOnly:
    """只看不判：渲染不写会话观察面（never feeds back into routing）。"""

    def test_render_does_not_mutate_answers_or_coords(self):
        s = make_session(creator_primary="plot")
        s.answers["剧情.core_dilemma"] = "答案"
        init_impulse_coords(s)
        before = dict(s.impulse_coords)
        render_persona_card(s)
        assert s.answers["剧情.core_dilemma"] == "答案"
        assert s.impulse_coords["axis"] == before["axis"]
        assert s.impulse_coords["confidence"] == before["confidence"]
        assert s.impulse_coords["audit"] == before["audit"]
        assert s.impulse_coords["reorder_count"] == before["reorder_count"]

    def test_render_lazy_init_idempotent(self):
        s = make_session(creator_primary="plot")
        c1 = render_persona_card(s)
        c2 = render_persona_card(s)
        assert c1 == c2  # 重复渲染幂等（init 只发生一次）


class TestEntrySunsetInterface:
    """入口单选 sunset：接口存在、默认关闭（plan §281 本期只留接口）。"""

    def test_default_off_returns_base_weight_unchanged(self, monkeypatch):
        monkeypatch.delenv("A1_ENTRY_SUNSET_ENABLED", raising=False)
        s = make_session(
            creator_primary="plot", creator_profile_source="impulse_cards")
        init_impulse_coords(s)
        # 选卡高置信起步 0.7 + pack_applied(+0.1)（浮点）→ ≥0.8 达阈值
        apply_signal(s, "pack_applied")
        assert entry_card_weight(s) == 1.0
        assert entry_card_weight(s, base_weight=0.4) == 0.4

    def test_disabled_even_without_coords(self, monkeypatch):
        monkeypatch.delenv("A1_ENTRY_SUNSET_ENABLED", raising=False)
        assert entry_card_weight(make_session()) == 1.0

    def test_enabled_flag_decays_mature_signal(self, monkeypatch):
        monkeypatch.setenv("A1_ENTRY_SUNSET_ENABLED", "1")
        s = make_session(
            creator_primary="plot", creator_profile_source="impulse_cards")
        init_impulse_coords(s)
        # 选卡高置信起步 0.7 + pack_applied(+0.1)（浮点）→ ≥0.8 达阈值
        apply_signal(s, "pack_applied")
        assert entry_card_weight(s) < 1.0

    def test_enabled_flag_immature_signal_undecayed(self, monkeypatch):
        monkeypatch.setenv("A1_ENTRY_SUNSET_ENABLED", "1")
        s = make_session()  # 说不清 = 低置信起步
        init_impulse_coords(s)
        assert s.impulse_coords["confidence"] < 0.5
        assert entry_card_weight(s) == 1.0

    def test_deterministic(self, monkeypatch):
        monkeypatch.setenv("A1_ENTRY_SUNSET_ENABLED", "1")
        ws = [
            entry_card_weight(make_session(creator_primary="romance"))
            for _ in range(2)
        ]
        assert ws[0] == ws[1]
