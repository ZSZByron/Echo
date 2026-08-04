"""Seed Engine — 双向概念映射统一编排引擎。

将概念解析→缺失检测→规则先导→LLM 补全→循环校验→用户确认→规则回馈
串成完整管线。

使用方式：
    engine = SeedEngine(provider)
    result = await engine.generate("古代水晶祭坛", preset_id="dark_fantasy_dungeon")
    # result.concept_node → 五维闭环 ConceptNode
    # result.cycle_reports → 循环一致性报告
    # result.rule_matches → 规则匹配命中

    # 用户确认后回馈规则
    engine.confirm_and_learn(result)
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider
from app.models.concept import (
    FIVE_DIMENSIONS,
    ConceptNode,
    ContentSource,
    DimensionFillLevel,
    SeedType,
)
from app.domains.creation.seed.backward_generator import backward_generate
from app.domains.creation.seed.cycle_checker import CycleReport, cycle_check_multi
from app.domains.creation.seed.gap_detector import GapDetectionResult, detect_gaps
from app.domains.creation.constraint.rule_mapper import RuleMatch, RuleTable

# ---------------------------------------------------------------------------
# 结果模型
# ---------------------------------------------------------------------------

class GenerationResult(BaseModel):
    """单次世界生成的完整结果。

    Attributes:
        concept_node: 最终的五维闭环 ConceptNode。
        gaps: 缺失检测报告。
        rule_matches: 每个维度的规则匹配结果。
        cycle_reports: 循环一致性校验报告列表。
        elapsed_seconds: 总耗时（秒）。
        errors: 生成过程中的非致命错误列表。
    """

    concept_node: ConceptNode
    gaps: GapDetectionResult | None = None
    rule_matches: dict[str, list[RuleMatch]] = Field(default_factory=dict)
    cycle_reports: list[CycleReport] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """是否所有维度都已填充且循环校验通过。"""
        if self.concept_node.empty_dimensions():
            return False
        return all(r.is_consistent for r in self.cycle_reports)

    def summary(self) -> str:
        """生成人类可读的摘要。"""
        lines = [
            f"种子: {self.concept_node.raw_input}",
            f"类型: {self.concept_node.detected_type.value}",
            f"已填充: {len(self.concept_node.filled_dimensions())}/{len(FIVE_DIMENSIONS)} 维度",
        ]
        if self.cycle_reports:
            consistent = sum(1 for r in self.cycle_reports if r.is_consistent)
            lines.append(f"循环校验: {consistent}/{len(self.cycle_reports)} 通过")
        if self.errors:
            lines.append(f"错误: {len(self.errors)} 个")
        lines.append(f"耗时: {self.elapsed_seconds:.1f}s")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 引擎
# ---------------------------------------------------------------------------

class SeedEngine:
    """双向概念映射统一编排引擎。

    持有一个 LLMProvider 实例和一个 RuleTable 实例，
    可重复调用 generate() 生成多个世界。
    """

    def __init__(
        self,
        provider: LLMProvider,
        rule_table: RuleTable | None = None,
    ) -> None:
        """初始化引擎。

        Args:
            provider: LLM Provider 实例。
            rule_table: 规则映射表，为 None 则从默认路径加载。
        """
        self._provider = provider
        self._rule_table = rule_table or RuleTable.load()

    # --- 主入口 ---

    async def generate(
        self,
        raw_input: str,
        seed_type: SeedType | str | None = None,
        seed_content: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        preset_id: str | None = None,
        enable_cycle_check: bool = True,
    ) -> GenerationResult:
        """从任意输入生成五维闭环世界。

        Args:
            raw_input: 用户原始输入文本。
            seed_type: 种子类型（如 "asset"），为 None 则尝试自动检测。
            seed_content: 种子内容（为 None 则用 raw_input 作为内容）。
            tags: 语义标签（为 None 则从 raw_input 简单提取）。
            preset_id: TRPG 预设 ID（影响生成风格）。
            enable_cycle_check: 是否启用循环一致性校验。

        Returns:
            GenerationResult: 完整生成结果。
        """
        import time
        start = time.time()

        errors: list[str] = []

        # Step 1: 概念解析
        node = self._parse_concept(
            raw_input, seed_type, seed_content, tags, preset_id,
        )

        # Step 2: 缺失检测
        gaps = detect_gaps(node)

        # Step 3: 规则匹配 + 反向生成
        rule_matches: dict[str, list[RuleMatch]] = {}
        style_guide = self._get_style_guide(preset_id)

        seed_dim = node.get_seed_dimension()
        if seed_dim and seed_content is not None:
            seed_content_dict = seed_content
        elif seed_dim:
            seed_content_dict = {"name": raw_input, "description": raw_input}
        else:
            # MIXED 类型 — 无法定向推理，退化为全维度 LLM 填充
            seed_dim = None
            seed_content_dict = {}

        # 填充每个缺失维度
        for gap in gaps.gaps:
            target_dim = gap.dimension
            if seed_dim:
                # 有种子维度 → 反向推理
                hints = self._match_rules(tags or [], target_dim, style_guide)
                rule_matches[target_dim] = hints
                try:
                    content = await backward_generate(
                        seed_dim=seed_dim,
                        seed_content=seed_content_dict,
                        target_dim=target_dim,
                        provider=self._provider,
                        style_guide=style_guide,
                        rule_hints=[h.rule.model_dump() for h in hints],
                    )
                    node.set_content(
                        target_dim, content,
                        source=ContentSource.BACKWARD_INFERRED,
                        confidence=0.75,
                    )
                except Exception as e:
                    errors.append(f"{target_dim} generation failed: {e}")
            else:
                # 无种子维度 → 使用通用填充
                try:
                    content = await self._generic_fill(
                        node, target_dim, style_guide,
                    )
                    node.set_content(
                        target_dim, content,
                        source=ContentSource.LLM_GENERATED,
                        confidence=0.6,
                    )
                except Exception as e:
                    errors.append(f"{target_dim} generic fill failed: {e}")

        # Step 4: 循环一致性校验
        cycle_reports: list[CycleReport] = []
        if enable_cycle_check and seed_dim:
            generated_dims = {
                dim: node.get_content(dim)
                for dim in node.filled_dimensions()
                if dim != seed_dim and node.get_content(dim) is not None
            }
            if generated_dims and seed_content_dict:
                try:
                    cycle_reports = await cycle_check_multi(
                        seed_content=seed_content_dict,
                        seed_dim=seed_dim,
                        generated=generated_dims,
                        provider=self._provider,
                    )
                    # 标记通过校验的维度
                    for report in cycle_reports:
                        if report.is_consistent:
                            dim_status = node.dimensions.get(report.target_dim)
                            if dim_status:
                                dim_status.source = ContentSource.CYCLE_VERIFIED
                                dim_status.confidence = min(
                                    1.0, dim_status.confidence + 0.1
                                )
                except Exception as e:
                    errors.append(f"cycle check failed: {e}")

        elapsed = time.time() - start

        return GenerationResult(
            concept_node=node,
            gaps=gaps,
            rule_matches=rule_matches,
            cycle_reports=cycle_reports,
            elapsed_seconds=elapsed,
            errors=errors,
        )

    # --- 用户确认 + 规则回馈 ---

    def confirm_and_learn(self, result: GenerationResult) -> list[str]:
        """用户确认生成结果后，回馈规则到规则表。

        从已确认的 (tags, target_dim, content) 中提取规则，
        追加到 RuleTable 并持久化。

        Args:
            result: 用户确认的生成结果。

        Returns:
            新增/更新的规则 ID 列表。
        """
        learned_ids: list[str] = []
        tags = result.concept_node.tags
        seed_dim = result.concept_node.get_seed_dimension()

        for dim in result.concept_node.filled_dimensions():
            if dim == seed_dim:
                continue

            content = result.concept_node.get_content(dim)
            if not content:
                continue

            mapping = {
                "source_tags": tags,
                "target_dim": dim,
                "rule": self._extract_rule_text(content, dim),
                "template": self._extract_template(content, dim),
                "source_seed": result.concept_node.raw_input[:50],
            }
            rule = self._rule_table.learn(mapping)
            learned_ids.append(rule.id)

        if learned_ids:
            self._rule_table.save()

        return learned_ids

    # --- 内部方法 ---

    def _parse_concept(
        self,
        raw_input: str,
        seed_type: SeedType | str | None,
        seed_content: dict[str, Any] | None,
        tags: list[str] | None,
        preset_id: str | None,
    ) -> ConceptNode:
        """解析输入为 ConceptNode。"""
        # 归一化 seed_type
        if seed_type is None:
            detected = SeedType.MIXED
        elif isinstance(seed_type, str):
            try:
                detected = SeedType(seed_type)
            except ValueError:
                detected = SeedType.MIXED
        else:
            detected = seed_type

        # 简单标签提取（如果未提供）
        if tags is None:
            tags = self._extract_tags(raw_input)

        node = ConceptNode(
            raw_input=raw_input,
            detected_type=detected,
            tags=tags,
            preset_id=preset_id,
        )

        # 设置种子维度内容
        if detected != SeedType.MIXED:
            seed_dim = detected.value
            content = seed_content or {"name": raw_input, "description": raw_input}
            node.set_content(
                seed_dim, content,
                source=ContentSource.INPUT,
                confidence=1.0,
            )

        return node

    def _extract_tags(self, text: str) -> list[str]:
        """简单的标签提取（基于关键词匹配）。

        实际生产中可以替换为更复杂的 NLP。
        """
        # 基础关键词 → 标签映射
        keyword_map = {
            "水晶": ["crystal", "magical"],
            "机械": ["machine", "mechanical"],
            "守护": ["guardian"],
            "古代": ["ancient"],
            "祭坛": ["altar", "ritual"],
            "星辰": ["stars"],
            "文明": ["ancient_civilization"],
            "改造": ["biological_modification"],
            "植入": ["implant"],
            "地下": ["underground"],
            "魔法": ["magical"],
            "恐怖": ["horror", "fear"],
            "机械体": ["cybernetic"],
            "废墟": ["ruins"],
        }
        tags: list[str] = []
        for keyword, mapped in keyword_map.items():
            if keyword in text:
                tags.extend(mapped)
        return list(set(tags)) if tags else ["generic"]

    def _match_rules(
        self,
        tags: list[str],
        target_dim: str,
        style_guide: dict[str, Any] | None,
    ) -> list[RuleMatch]:
        """匹配规则表 + 预设 mapping_logic。"""
        # 1. 持久化规则表
        matches = self._rule_table.match(tags, target_dim)

        # 2. 预设 mapping_logic 作为补充
        if style_guide and not matches:
            mapping_logic = style_guide.get("mapping_logic", [])
            for rule in mapping_logic:
                if rule.get("target_dim") == target_dim:
                    source_tags = rule.get("source_tags", [])
                    tag_set = set(tags)
                    source_set = set(source_tags)
                    if tag_set & source_set:
                        from app.domains.creation.constraint.rule_mapper import RuleEntry
                        matches.append(RuleMatch(
                            rule=RuleEntry(
                                id=f"PRESET_{target_dim}",
                                source_tags=source_tags,
                                target_dim=target_dim,
                                rule=rule.get("rule", ""),
                                template=rule.get("template", ""),
                                confidence=0.7,
                            ),
                            matched_tags=list(tag_set & source_set),
                            score=0.5,
                        ))
                        break

        return matches

    def _get_style_guide(self, preset_id: str | None) -> dict[str, Any] | None:
        """获取预设风格指令。"""
        if not preset_id:
            return None
        try:
            from experiments.trpg_presets import get_style_guide
            return get_style_guide(preset_id)
        except Exception:
            return None

    async def _generic_fill(
        self,
        node: ConceptNode,
        target_dim: str,
        style_guide: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """无种子维度时的通用填充（MIXED 类型输入）。"""
        import json

        # 收集已有维度作为上下文
        existing = {}
        for dim in FIVE_DIMENSIONS:
            content = node.get_content(dim)
            if content is not None:
                existing[dim] = content

        system_parts = [
            f"你是一个游戏世界设计师。请根据已有内容生成{target_dim}维度的内容。",
        ]
        if style_guide:
            voice = style_guide.get("voice_prompt", "")
            if voice:
                system_parts.append(f"\n## 叙述风格\n{voice}")

        system_parts.append("\n输出必须是合法 JSON，所有文本使用中文。")

        user_content = (
            f"输入概念: {node.raw_input}\n"
            f"标签: {', '.join(node.tags)}\n"
        )
        if existing:
            user_content += (
                f"已有维度内容:\n"
                f"{json.dumps(existing, ensure_ascii=False, indent=2)}\n\n"
            )
        user_content += f"请生成 {target_dim} 维度的内容。"

        messages = [
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user", "content": user_content},
        ]
        return await self._provider.chat_json(messages)

    def _extract_rule_text(self, content: dict[str, Any], dim: str) -> str:
        """从生成内容中提取规则文本。"""
        if dim == "constraint":
            return content.get("rule", str(content)[:100])
        if dim == "story":
            return content.get("description", str(content)[:100])
        if dim == "event":
            return content.get("description", str(content)[:100])
        if dim == "culture":
            values = content.get("values", [])
            return f"价值观: {', '.join(values[:3])}"
        if dim == "asset":
            return content.get("description", str(content)[:100])
        return str(content)[:100]

    def _extract_template(self, content: dict[str, Any], dim: str) -> str:
        """从生成内容中提取模板。"""
        name = content.get("name", "")
        if dim == "constraint":
            return content.get("rule", "")[:80]
        if dim == "story":
            return f"{{name}}: {{description}}" if name else ""
        if dim == "event":
            return f"当{{trigger}}时，{{name}}发生" if name else ""
        if dim == "culture":
            return f"{{cult_name}}：价值观{{values}}，美学{{aesthetics}}"
        if dim == "asset":
            return f"{{name}}：{{description}}" if name else ""
        return ""
