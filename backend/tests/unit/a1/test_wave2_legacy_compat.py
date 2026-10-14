# -*- coding: utf-8 -*-
"""T10（批E-2）：存量会话兼容全检（42 字段时代 · 无形状 fills · 零迁移承诺）。

四断言（施工单 T10 存量兼容口径）：
1. 旧字典（无波次二新五字段）model_validate 加载 → 新字段取默认（零迁移）。
2. 旧会话继续访谈：新答案按 ● 点路径落库（纯串，无形状包装）。
3. 旧会话完成度语义：配方字段答满 → is_preset_phase_complete 判真（不变）。
4. 旧无形状答案经 T9 确定性编译零新边（字节级一致已由
   .sisyphus/evidence/wave2-t9-regression-*.json SHA256 锁，此处引擎级复证）。

纪律：纯测试零生产代码；GREEN 为预期，RED 即存量兼容破坏（停手报告）。
"""
from __future__ import annotations

from app.domains.creation.a1.closing_gate import is_preset_phase_complete
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_COMPLETED,
    answer_view,
    handle_message,
    sync_position,
)
from app.domains.creation.a1.interviewer import FakeInterviewer, InterviewFill
from app.domains.creation.a1.live_projection import compile_value_shape_edges
from app.models.knowledge_graph import EdgeType

#: 波次二 A1Session additive 新字段（批A 三枚 + 批C 裁定两枚）。
WAVE2_NEW_FIELDS = (
    "material_pool",
    "list_thread_key",
    "list_thread_turns",
    "mirror_thread_active",
    "mirror_thread_turns",
)

#: 旧 42 字段时代故事线配方域（M12 剧情 9 + M11 角色 6，module.field 寻址）。
_LEGACY_PLOT_FIELDS = [
    ("剧情", "opening_event"), ("剧情", "core_dilemma"),
    ("剧情", "tension_hole"), ("剧情", "lead_chain"),
    ("剧情", "secret_layer"), ("剧情", "branch_trees"),
    ("剧情", "bound_characters"), ("剧情", "arc_direction"),
    ("剧情", "scene_hooks"),
    ("角色", "identity"), ("角色", "desire"), ("角色", "flaw"),
    ("角色", "key_relations"), ("角色", "arc_direction"),
    ("角色", "character_visual"),
]


def _legacy_session_dict() -> dict:
    """旧时代序列化会话：进行中状态 + 部分答案（含 branch_trees 纯串）。"""
    s = A1Session(
        session_id="s_legacy",
        user_id="u_legacy",
        recipe_id="plot",
        recipe_modules=["剧情", "角色"],
    )
    sync_position(s)
    s.answers["剧情.branch_trees"] = "成功端网但家散了；失败亡命江湖"
    s.answers["角色.key_relations"] = "妹妹（唯一软肋）"
    dump = s.model_dump()
    for key in WAVE2_NEW_FIELDS:  # 模拟旧持久层：无波次二键
        dump.pop(key, None)
    assert not (set(WAVE2_NEW_FIELDS) & set(dump)), "旧字典泄漏新字段"
    return dump


class TestLegacyDictLoad:
    def test_legacy_dict_loads_with_defaults(self):
        """旧字典加载零迁移：新五字段取默认（空/0/False）。"""
        legacy = A1Session.model_validate(_legacy_session_dict())
        assert legacy.material_pool == []
        assert legacy.list_thread_key == ""
        assert legacy.list_thread_turns == 0
        assert legacy.mirror_thread_active is False
        assert legacy.mirror_thread_turns == 0

    def test_legacy_answers_preserved_verbatim(self):
        legacy = A1Session.model_validate(_legacy_session_dict())
        assert legacy.answers["剧情.branch_trees"] == (
            "成功端网但家散了；失败亡命江湖"
        )


class TestLegacyContinueInterview:
    def test_new_answer_lands_as_plain_point(self):
        """旧会话继续访谈：新答案按 ● 纯串落库（无形状包装）。"""
        legacy = A1Session.model_validate(_legacy_session_dict())
        fake = FakeInterviewer(fills=[InterviewFill(
            module="角色", subfield="identity", value="他是干了二十年的老刑警",
        )])
        handle_message(legacy, "他是干了二十年的老刑警", fake)
        value = legacy.answers.get("角色.identity")
        assert value is not None, "新答案未落库"
        assert answer_view(value) == "他是干了二十年的老刑警", (
            "● 路径被形状包装污染"
        )


class TestLegacyCompletionGate:
    def test_legacy_completed_session_still_complete(self):
        """旧完成会话（phase 已完成 + 答案答满）升级后仍判完成（语义不变）。"""
        legacy = A1Session.model_validate(_legacy_session_dict())
        for module, field in _LEGACY_PLOT_FIELDS:
            legacy.answers[f"{module}.{field}"] = f"{field} 的旧答案"
        legacy.phase = PHASE_COMPLETED
        assert is_preset_phase_complete(legacy) is True, (
            "存量完成会话被升级后误判未完成（门禁口径漂移）"
        )

    def test_partial_legacy_session_still_incomplete(self):
        """进行中旧会话不被误判完成（双向口径）。"""
        legacy = A1Session.model_validate(_legacy_session_dict())
        assert is_preset_phase_complete(legacy) is False


class TestLegacyNoNewEdges:
    def test_legacy_plain_answers_produce_zero_shape_edges(self):
        """旧纯串答案 → 确定性编译零迁移/衔接边（T9 字节锁的引擎级复证）。"""
        legacy = A1Session.model_validate(_legacy_session_dict())
        for module, field in _LEGACY_PLOT_FIELDS:
            legacy.answers[f"{module}.{field}"] = f"{field} 的旧答案"
        _nodes, edges, _warnings = compile_value_shape_edges(legacy)
        shaped = [
            e for e in edges
            if e.edge_type in (EdgeType.MIGRATION, EdgeType.LINKAGE)
        ]
        assert shaped == [], f"旧会话被误产 {len(shaped)} 条形状边"
