# -*- coding: utf-8 -*-
"""M3 A2 产出模块入池 — 契约测试（先于实现，TDD RED）。

证据锚点（.sisyphus/evidence/a2-plan-mining-a2-specs.md）：
- 封闭三枚举逐字（S1:292-308 / S2:293-305）——"不允许添加或修改"。
- 骰子四步法（S2:449-466）：直投→reality_rule 判定→缺省+披露；等级词法
  70% 阈值；难度联动；边界钳制。
- signal_sources 溯源（S1:331-333 / S2:336）：全字段披露，"a1:模块.字段"/
  "rule:*"/"default" 三形态。
- 角色 4 相位封闭枚举 + 常量/变量/锚点（S1:339-358 / S2:340-367）；
  缺骰子 → DiceRequiredError（路由层转 409 missing_dice_template）。
- 主模组九节树冻结（S2:400-403）+ LLM module_compile 单点失败确定性
  降级（骨架 + ledger 披露）——LLM 只产文案（D-A2-4），结构数值全确定性。
- 注册（plan §248）：三件入 MODULE_POOL family="output"，signal_requirements
  声明输入依赖；产出模块不入任何配方（终局生产者，非问卷模块）。

D15 裁决：max_party_size=6；文档导出资源名 = doc。
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.creation.modules.character_projector import (
    DiceRequiredError,
    TemplatePhase,
    project_character_template,
)
from app.domains.creation.modules.dice_projector import (
    DEFAULT_STAT_CEILING,
    DEFAULT_STAT_FLOOR,
    DiceCoreType,
    DifficultySystem,
    GrowthSystem,
    project_dice_template,
)
from app.domains.creation.modules.main_module import (
    NINE_SECTION_HEADINGS,
    ScopeBoundary,
    compile_document,
    render_markdown,
)
from app.domains.creation.shared.module_registry import MODULE_POOL, RECIPES
from app.domains.creation.modules.output_modules import OUTPUT_MODULE_IDS
from app.domains.creation.a1.tier_map import module_tier_coverage

SIGNAL_ANSWERS: dict[str, str] = {
    "骰子设定.probability": "采用百分比骰进行判定",
    "骰子设定.dice_count": "2 枚 d10",
    "骰子设定.check_mode": "对抗检定",
    "骰子设定.success_check": "达到难度值即成功",
    "力量体系.cost": "每次施法消耗体力值",
    "世界本体.reality_rule": "世界由物质法则主导，魔法稀有",
    "设定边界.immutable_core": "神王不可被杀死",
    "力量体系.acquire": "通过试炼获取力量",
}


# ---------------------------------------------------------------------------
# 1. 封闭枚举（S2:293-305 / S2:340-345 逐字——不允许添加或修改）
# ---------------------------------------------------------------------------


class TestClosedEnums:
    def test_dice_core_type_values_verbatim(self):
        assert {e.value for e in DiceCoreType} == {
            "d20_modifier", "dice_pool", "percentage",
        }

    def test_growth_system_values_verbatim(self):
        assert {e.value for e in GrowthSystem} == {"slot", "tier", "hybrid"}

    def test_difficulty_system_values_verbatim(self):
        assert {e.value for e in DifficultySystem} == {
            "counter_value", "contextual", "hybrid",
        }

    def test_template_phase_values_verbatim(self):
        assert {e.value for e in TemplatePhase} == {
            "narrative", "mechanism", "resource", "direction",
        }


# ---------------------------------------------------------------------------
# 2. 骰子投影：确定性 + 四步法 + signal_sources 溯源
# ---------------------------------------------------------------------------


class TestDiceProjector:
    def test_deterministic_same_input_same_output(self):
        a = project_dice_template(
            SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        b = project_dice_template(
            SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert a.model_dump() == b.model_dump()

    def test_step1_direct_mapping_from_dice_module(self):
        t = project_dice_template(
            SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.dice_core is DiceCoreType.PERCENTAGE
        assert t.check_mode == "对抗检定"  # 直投 A1 骰子设定.check_mode
        assert t.success_check == "达到难度值即成功"
        assert t.cost_mechanism == "每次施法消耗体力值"  # 源：力量体系.cost

    def test_step1_reality_rule_fallback_when_dice_missing(self):
        answers = {"世界本体.reality_rule": "意志与信念塑造现实"}
        t = project_dice_template(
            answers, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.dice_core is DiceCoreType.DICE_POOL
        assert t.signal_sources["dice_core"] == "rule:reality_dominant"

    def test_step1_all_missing_defaults_with_disclosure(self):
        t = project_dice_template(
            {}, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.dice_core is DiceCoreType.D20_MODIFIER
        assert any("dice_defaults_used" in w for w in t.warnings)

    def test_signal_sources_cover_five_chains(self):
        t = project_dice_template(
            SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        for key in ("dice_core", "dice_source", "check_mode",
                    "success_check", "cost_mechanism", "growth_system",
                    "difficulty_system"):
            assert key in t.signal_sources, f"missing badge: {key}"
            src = t.signal_sources[key]
            assert src.startswith(("a1:", "rule:", "default")), src

    def test_growth_lexical_and_difficulty_linkage(self):
        answers = dict(SIGNAL_ANSWERS,
                       力量体系__placeholder="")  # noqa: F841
        answers.pop("力量体系__placeholder")
        t = project_dice_template(
            answers, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.growth_system in GrowthSystem
        assert t.difficulty_system in DifficultySystem
        assert len(t.difficulty_table) == 5  # 五档对照表（GM 直查）
        assert [row.label for row in t.difficulty_table] == [
            "日常", "简单", "标准", "困难", "极限",
        ]

    def test_growth_linkage_slot_to_counter_value(self):
        answers = {"力量体系.acquire": "每级解锁两个技能槽位配置"}
        t = project_dice_template(
            answers, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.growth_system is GrowthSystem.SLOT
        assert t.difficulty_system is DifficultySystem.COUNTER_VALUE

    def test_step2_dna_direct_signals(self):
        """玩法设计DNA.growth 直投信号（S2:454）：定量→slot / 定性→tier /
        双现→hybrid，先于词法兜底。"""
        base = {"骰子设定.probability": "d20"}
        cases = {
            "定量数值积累": (GrowthSystem.SLOT, DifficultySystem.COUNTER_VALUE),
            "定性位阶质变": (GrowthSystem.TIER, DifficultySystem.CONTEXTUAL),
            "定量与定性并存": (GrowthSystem.HYBRID, DifficultySystem.HYBRID),
        }
        for text, (growth, diff) in cases.items():
            t = project_dice_template(
                dict(base, **{"玩法设计DNA.growth": text}),
                graph_code="IP0001-TD1-v1",
                upstream_graph_code="IP0001-W1-v1",
            )
            assert t.growth_system is growth, text
            assert t.difficulty_system is diff, text
            assert t.signal_sources["growth_system"] == "a1:玩法设计DNA.growth"

    def test_step1_wording_variants(self):
        """probability 措辞→percentage/骰池；物质措辞 reality_rule→d20。"""
        gc, up = "IP0001-TD1-v1", "IP0001-W1-v1"
        pct = project_dice_template(
            {"骰子设定.probability": "成功率以百分比衡量"},
            graph_code=gc, upstream_graph_code=up)
        assert pct.dice_core is DiceCoreType.PERCENTAGE
        pool = project_dice_template(
            {"骰子设定.probability": "骰池判定计成功数"},
            graph_code=gc, upstream_graph_code=up)
        assert pool.dice_core is DiceCoreType.DICE_POOL
        mat = project_dice_template(
            {"世界本体.reality_rule": "物质与物理法则主导"},
            graph_code=gc, upstream_graph_code=up)
        assert mat.dice_core is DiceCoreType.D20_MODIFIER
        assert mat.signal_sources["dice_core"] == "rule:reality_dominant"

    def test_step4_level_cap_clamp(self):
        t = project_dice_template(
            {}, graph_code="IP0001-TD1-v1", upstream_graph_code="IP0001-W1-v1",
            constraints=["等级上限 12"],
        )
        assert t.level_cap == 12

    def test_step4_boundary_clamp_from_constraints(self):
        t = project_dice_template(
            SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
            constraints=["属性不超过 18", "属性不低于 8"],
        )
        assert t.stat_ceiling == 18
        assert t.stat_floor == 8

    def test_step4_sparse_constraints_default_with_disclosure(self):
        t = project_dice_template(
            {}, graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.stat_floor == DEFAULT_STAT_FLOOR
        assert t.stat_ceiling == DEFAULT_STAT_CEILING
        assert any("stat_bounds_default_used" in w for w in t.warnings)

    def test_branches_dice_pool_wording_and_level_cap(self):
        t = project_dice_template(
            {"骰子设定.probability": "掷骰池计成功数",
             "骰子设定.check_mode": "池判定",
             "骰子设定.success_check": "3 个成功即成",
             "骰子设定.dice_count": "6 枚",
             "世界本体.reality_rule": "意志凝聚现实",
             "设定边界.immutable_core": "神不可杀"},
            graph_code="IP0001-TD1-v1",
            upstream_graph_code="IP0001-W1-v1",
            constraints=["属性不低于 6", "属性不超过 20", "等级上限 12"],
        )
        assert t.dice_core is DiceCoreType.DICE_POOL
        assert t.level_cap == 12
        assert t.signal_sources["dice_core"] == "a1:骰子设定.probability"

    def test_growth_dna_hybrid_and_qualitative(self):
        both = project_dice_template(
            {"玩法设计DNA.growth": "定量数值与定性位阶并存"},
            graph_code="T", upstream_graph_code="U",
        )
        qual = project_dice_template(
            {"玩法设计DNA.growth": "以位阶质变为成长主轴"},
            graph_code="T", upstream_graph_code="U",
        )
        assert both.growth_system is GrowthSystem.HYBRID
        assert both.difficulty_system is DifficultySystem.HYBRID
        assert qual.growth_system is GrowthSystem.TIER
        assert qual.signal_sources["growth_system"] == "a1:玩法设计DNA.growth"

    def test_growth_lexical_slot_and_reality_percentage(self):
        slot = project_dice_template(
            {"力量体系.acquire": "解锁技能槽位配置"},
            graph_code="T", upstream_graph_code="U",
        )
        pct = project_dice_template(
            {"世界本体.reality_rule": "意志主导",
             "骰子设定.probability": "以百分比对冲命运"},
            graph_code="T", upstream_graph_code="U",
        )
        assert slot.growth_system is GrowthSystem.SLOT
        assert slot.difficulty_system is DifficultySystem.COUNTER_VALUE
        assert pct.dice_core is DiceCoreType.PERCENTAGE
        will_pool = project_dice_template(
            {"世界本体.reality_rule": "意志主导，信念决定成败"},
            graph_code="T", upstream_graph_code="U",
        )
        assert will_pool.dice_core is DiceCoreType.DICE_POOL  # S2:452 措辞缺省

    def test_character_will_dominant_narrative_core_and_defaults(self):
        t = project_character_template(
            {"世界本体.reality_rule": "意志与信念塑造现实"},
            _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert "narrative" in t.core_phases
        defaults = project_character_template(
            {}, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert any("core_phase_defaults_used" in w
                   for w in defaults.warnings)
        assert defaults.signal_sources["anchors"] in ("a1:open_questions",
                                                      "default")


# ---------------------------------------------------------------------------
# 3. 角色投影：4 相位 + 常量/变量/锚点 + 依赖骰子
# ---------------------------------------------------------------------------


def _dice() -> object:
    return project_dice_template(
        SIGNAL_ANSWERS, graph_code="IP0001-TD1-v1",
        upstream_graph_code="IP0001-W1-v1",
    )


class TestCharacterProjector:
    def test_missing_dice_raises_dependency_error(self):
        with pytest.raises(DiceRequiredError):
            project_character_template(
                SIGNAL_ANSWERS, None, graph_code="IP0001-TC1-v1",
                upstream_graph_code="IP0001-W1-v1",
            )

    def test_deterministic_same_input_same_output(self):
        a = project_character_template(
            SIGNAL_ANSWERS, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        b = project_character_template(
            SIGNAL_ANSWERS, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert a.model_dump() == b.model_dump()

    def test_four_phases_with_two_core(self):
        t = project_character_template(
            SIGNAL_ANSWERS, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert set(t.phases) == {p.value for p in TemplatePhase}
        assert len(t.core_phases) == 2
        assert len(t.secondary_phases) == 2
        assert not set(t.core_phases) & set(t.secondary_phases)
        # 物质主导 → 机制相位定调（reality_dominant）
        assert "mechanism" in t.core_phases

    def test_constants_variables_anchors_allocation(self):
        t = project_character_template(
            SIGNAL_ANSWERS, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
            open_questions=["你的角色为何踏上旅途？"],
        )
        all_constants = [c for p in t.phases.values() for c in p.constants]
        assert any("神王不可被杀死" in c for c in all_constants)  # 设定边界 → 常量
        all_variables = [v for p in t.phases.values() for v in p.variables]
        assert any("试炼" in v for v in all_variables)  # 力量体系.acquire → 变量
        all_anchors = [a for p in t.phases.values() for a in p.anchors]
        assert any("为何踏上旅途" in a for a in all_anchors)  # open_questions → 锚点

    def test_dice_numbers_injected_into_mechanism(self):
        dice = _dice()
        t = project_character_template(
            SIGNAL_ANSWERS, dice, graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        mech = t.phases["mechanism"]
        assert any(str(dice.stat_floor) in c for c in mech.constants)
        assert any(dice.graph_code in c for c in mech.constants)

    def test_signal_sources_badges_present(self):
        t = project_character_template(
            SIGNAL_ANSWERS, _dice(), graph_code="IP0001-TC1-v1",
            upstream_graph_code="IP0001-W1-v1",
        )
        assert t.dice_template_code == "IP0001-TD1-v1"
        for key in ("core_phases", "constants", "variables"):
            assert key in t.signal_sources


# ---------------------------------------------------------------------------
# 4. 主模组文字版：九节树 + LLM 单点 + 确定性降级（免费线）
# ---------------------------------------------------------------------------


class TestMainModuleDocument:
    def test_nine_section_tree_frozen(self):
        assert NINE_SECTION_HEADINGS == (
            "模组概述", "世界背景摘要", "舞台：区域与分区", "时代与主线",
            "平行剧情挂点", "势力与冲突", "骰子规则", "角色创建指南",
            "GM 边界须知",
        )

    def test_scope_boundary_d15_defaults(self):
        sb = ScopeBoundary()
        assert sb.max_party_size == 6  # D15：S2 值胜出
        assert sb.source == "default"

    def test_zero_llm_fallback_produces_usable_markdown(self):
        doc, ledger = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=None,
        )
        assert len(doc.sections) == 9
        assert [s.heading for s in doc.sections] == list(NINE_SECTION_HEADINGS)
        # 答案原文进骨架（结构确定性，LLM 缺席只影响文案）
        assert "剑" in doc.sections[3].body or doc.sections[3].body == ""
        md = render_markdown(doc)
        assert md.startswith("# 星陨大陆：主模组")
        assert "## 模组概述" in md
        assert "## GM 边界须知" in md
        assert any("module_compile_degraded" in e["detail"] for e in ledger)

    def test_llm_path_only_supplies_copy_structure_identical(self):
        class FakeProvider:
            async def chat_json(self, messages, **kw):
                return {
                    "module_fantasy": "一场关于遗忘之神的闹剧",
                    "sections": {h: f"（LLM 文案：{h}）"
                                 for h in NINE_SECTION_HEADINGS},
                }

        doc_llm, ledger_llm = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(),
        )
        doc_fb, _ = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=None,
        )
        # 结构数值全确定性：章节树/scope 两个路径逐字节一致（D-A2-4）
        assert [s.heading for s in doc_llm.sections] == \
            [s.heading for s in doc_fb.sections]
        assert doc_llm.scope_boundary == doc_fb.scope_boundary
        assert doc_llm.module_fantasy == "一场关于遗忘之神的闹剧"
        assert not any("module_compile_degraded" in e["detail"]
                       for e in ledger_llm)

    def test_llm_failure_falls_back_deterministically(self):
        class BoomProvider:
            async def chat_json(self, messages, **kw):
                raise RuntimeError("network down")

        doc, ledger = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=BoomProvider(),
        )
        assert len(doc.sections) == 9
        assert any("module_compile_degraded" in e["detail"] for e in ledger)

    def test_deterministic_same_input_same_skeleton(self):
        a, _ = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=None,
        )
        b, _ = compile_document(
            SIGNAL_ANSWERS, title="星陨大陆：主模组", ip_name="星陨大陆",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=None,
        )
        assert a.sections == b.sections

    def test_invalid_llm_payload_ignored(self):
        class BadShape:
            async def chat_json(self, messages, **kw):
                return {"unexpected": "shape"}

        doc, ledger = compile_document(
            SIGNAL_ANSWERS, title="t", ip_name="ip",
            graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=BadShape(),
        )
        assert len(doc.sections) == 9
        assert any("module_compile_degraded" in e["detail"] for e in ledger)


# ---------------------------------------------------------------------------
# 5. 注册表：产出模块入池（family=output）+ 不入配方
# ---------------------------------------------------------------------------


class TestRegistryOutputModules:
    def test_eight_output_modules_in_pool(self):
        """§96 逐字锁定：L2×5 + L3×3 = 8 件产出模块全量入池。"""
        expected = (
            "主模组文字版", "骰子投影", "角色投影",
            "玩法设计完整形态", "商业分析报告",
            "场景扩写", "资产管线", "叙事渲染",
        )
        assert len(expected) == 8
        for mid in expected:
            assert mid in MODULE_POOL, mid
            assert MODULE_POOL[mid].family == "output"

    def test_output_module_ids_order_locked(self):
        assert OUTPUT_MODULE_IDS == (
            "主模组文字版", "骰子投影", "角色投影",
            "玩法设计完整形态", "商业分析报告",
            "场景扩写", "资产管线", "叙事渲染",
        )

    def test_all_output_modules_signal_requirements_valid(self):
        """全部产出模块声明 signal_requirements，且档位在闭集内。"""
        from app.domains.creation.modules.output_modules import (
            OUTPUT_MODULES, SIGNAL_LEVELS,
        )
        for m in OUTPUT_MODULES:
            assert m["signal_requirements"], m["id"]
            assert all(v in SIGNAL_LEVELS
                       for v in m["signal_requirements"].values()), m["id"]

    def test_signal_requirements_declared(self):
        dice = MODULE_POOL["骰子投影"].signal_requirements
        assert dice["骰子设定.probability"] == "optional"
        assert "世界本体.reality_rule" in dice  # reality_rule 回退链
        assert "力量体系.cost" in dice  # cost 五链
        char = MODULE_POOL["角色投影"].signal_requirements
        assert char["骰子投影"] == "hard"  # 缺 → 409 missing_dice_template
        doc = MODULE_POOL["主模组文字版"].signal_requirements
        assert all(v in ("required", "optional", "hard")
                   for v in doc.values())

    def test_output_modules_never_in_recipes(self):
        for recipe in RECIPES.values():
            overlap = set(recipe.module_ids) & {
                "主模组文字版", "骰子投影", "角色投影",
            }
            assert not overlap, f"{recipe.id} must not contain output modules"

    def test_pool_tier_coverage_still_empty(self):
        assert module_tier_coverage() == []

    def test_output_modules_have_no_questionnaire_fields(self):
        for mid in ("主模组文字版", "骰子投影", "角色投影"):
            assert MODULE_POOL[mid].fields == []
