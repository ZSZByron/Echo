"""真实语义编译器 - 断点A三级匹配实现

三级匹配级联（前两级零LLM成本）：
    Level1 种子库级：seed_library 精确/归一化匹配（零LLM）
    Level2 词典规则级：同义词/关键词规则命中词典枚举值（零LLM）
    Level3 LLM级：provider.chat_json 从封闭枚举候选中选值，逐一校验

铁律：
    编译器绝不产生词典外枚举值。每条 FieldWrite 的 value 在返回前
    均对照 tag_dictionary.get_enum_values 校验，非法值直接丢弃。

降级链路：
    L1未命中 → L2未命中 → L3(provider为None/异常/非法JSON/全部值被丢弃)
    → CompileResult(writes=[], classification_proposal=...)
"""

from __future__ import annotations

import asyncio

from app.ai.provider import LLMProvider
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    CompileResult,
    FieldWrite,
    Suggestion,
)
from app.models.tag_dictionary import get_enum_values


# Level2 规则表：关键词（小写）→ (维度, 标签, 枚举值)
# 枚举值必须存在于 tag_dictionary.yaml，加载时逐一校验
_RULE_TABLE: dict[str, tuple[str, str, str]] = {
    # LAW.world_structure
    "浮空岛": ("LAW", "world_structure", "FLOATING_ISLANDS"),
    "浮岛": ("LAW", "world_structure", "FLOATING_ISLANDS"),
    "floating islands": ("LAW", "world_structure", "FLOATING_ISLANDS"),
    "球形世界": ("LAW", "world_structure", "SPHERE"),
    "树形世界": ("LAW", "world_structure", "TREE"),
    "世界树": ("LAW", "world_structure", "TREE"),
    "扁平世界": ("LAW", "world_structure", "FLAT_PLANE"),
    "环形世界": ("LAW", "world_structure", "TORUS"),
    "塔式世界": ("LAW", "world_structure", "TOWER"),
    "洞穴世界": ("LAW", "world_structure", "CAVE_SYSTEM"),
    "海洋世界": ("LAW", "world_structure", "OCEAN_WORLD"),
    # LAW.gravity
    "高重力": ("LAW", "gravity", "HIGH"),
    "低重力": ("LAW", "gravity", "LOW"),
    "无重力": ("LAW", "gravity", "ZERO"),
    "零重力": ("LAW", "gravity", "ZERO"),
    "重力多变": ("LAW", "gravity", "VARIABLE"),
    # LAW.divine_intervention
    "神不存在": ("LAW", "divine_intervention", "NONE"),
    "神明干涉": ("LAW", "divine_intervention", "DIRECT"),
    # ACT.dice_mode
    "无骰": ("ACT", "dice_mode", "DICELESS"),
    "d20": ("ACT", "dice_mode", "LINEAR_D20"),
    "3d6": ("ACT", "dice_mode", "BELL_CURVE_3D6"),
    "d100": ("ACT", "dice_mode", "D100"),
}


class RealSemanticCompiler:
    """三级匹配真实编译器

    实现 shared.semantic_compiler.SemanticCompiler 契约。
    L1/L2 命中零LLM成本；L3 兜底调用 provider.chat_json。
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        seed_library: dict[str, list[FieldWrite]] | None = None,
    ) -> None:
        self._provider = provider
        self._seed_library: dict[str, list[FieldWrite]] = {
            k.lower(): v for k, v in (seed_library or {}).items()
        }
        # L2规则表启动校验：规则值必须在词典内（铁律前置检查）
        self._rules = {
            kw: rule
            for kw, rule in _RULE_TABLE.items()
            if self._is_valid_field(rule[0], rule[1], rule[2])
        }

    # ---------- 契约方法 ----------

    def compile(self, session_id: str, text: str) -> CompileResult:
        """编译自然语言 → 结构化指令（三级级联）"""
        # Level1 种子库级
        writes = self._match_seed_library(text)
        if writes:
            return CompileResult(writes=writes)

        # Level2 词典规则级
        writes = self._match_rules(text)
        if writes:
            return CompileResult(writes=writes)

        # Level3 LLM级
        writes = self._match_llm(text)
        if writes:
            return CompileResult(writes=writes)

        # 全失败 → 创新语句进分类提案（不落盘）
        return self._fallback_proposal(text)

    # ---------- Level1 种子库级 ----------

    def _match_seed_library(self, text: str) -> list[FieldWrite]:
        """种子库归一化匹配（大小写不敏感的包含匹配）"""
        text_lower = text.lower()
        matched: list[FieldWrite] = []
        for keyword, kw_writes in self._seed_library.items():
            if keyword in text_lower:
                matched.extend(self._validate_writes(kw_writes))
        return matched

    # ---------- Level2 词典规则级 ----------

    def _match_rules(self, text: str) -> list[FieldWrite]:
        """词典同义词/关键词规则匹配"""
        text_lower = text.lower()
        matched: list[FieldWrite] = []
        seen: set[tuple[str, str]] = set()
        for keyword, (dim, tag, value) in self._rules.items():
            if keyword in text_lower and (dim, tag) not in seen:
                matched.append(FieldWrite(field=f"{dim}.{tag}", value=value))
                seen.add((dim, tag))  # 同维度同标签只写一次
        return matched

    # ---------- Level3 LLM级 ----------

    def _match_llm(self, text: str) -> list[FieldWrite]:
        """LLM级兜底：封闭枚举候选 + 逐一校验"""
        if self._provider is None:
            return []
        try:
            result = asyncio.run(
                self._provider.chat_json(
                    [
                        {"role": "system", "content": self._build_llm_prompt()},
                        {"role": "user", "content": text},
                    ]
                )
            )
        except Exception:
            return []
        return self._parse_llm_response(result)

    def _build_llm_prompt(self) -> str:
        """构建封闭枚举候选 prompt（仅暴露词典内常见维度）"""
        lines = [
            "你是TRPG世界设定的语义编译器。从用户文本中提取设定，",
            "只能从以下封闭枚举中选值，返回JSON：",
            '{"writes": [{"field": "DIM.tag", "value": "枚举值"}], "confidence": 0.9}',
            "可用枚举：",
        ]
        for dim, tag in self._candidate_fields():
            values = get_enum_values(dim, tag)
            lines.append(f"- {dim}.{tag}: {', '.join(values)}")
        lines.append("若文本无法映射到任何枚举值，返回空writes列表。")
        return "\n".join(lines)

    def _candidate_fields(self) -> list[tuple[str, str]]:
        """LLM候选字段列表（LAW+ACT核心维度）"""
        return [
            ("LAW", "world_structure"),
            ("LAW", "gravity"),
            ("LAW", "conservation"),
            ("LAW", "divine_intervention"),
            ("LAW", "afterlife"),
            ("ACT", "dice_mode"),
            ("ACT", "check_direction"),
        ]

    def _parse_llm_response(self, result: dict) -> list[FieldWrite]:
        """解析LLM返回并逐一校验词典合法性，非法值丢弃"""
        raw_writes = result.get("writes", [])
        if not isinstance(raw_writes, list):
            return []
        validated: list[FieldWrite] = []
        for item in raw_writes:
            if not isinstance(item, dict):
                continue
            field, value = item.get("field"), item.get("value")
            if not isinstance(field, str) or not isinstance(value, str):
                continue
            parts = field.split(".", 1)
            if len(parts) != 2:
                continue
            if self._is_valid_field(parts[0], parts[1], value):
                validated.append(FieldWrite(field=field, value=value))
        return validated

    # ---------- 校验工具 ----------

    @staticmethod
    def _is_valid_field(dim: str, tag: str, value: str) -> bool:
        """铁律校验：value 必须在词典封闭枚举内"""
        try:
            return value in get_enum_values(dim, tag)
        except ValueError:
            return False

    def _validate_writes(self, writes: list[FieldWrite]) -> list[FieldWrite]:
        """批量校验 FieldWrite 列表（种子库数据同样过铁律）"""
        validated: list[FieldWrite] = []
        for w in writes:
            parts = w.field.split(".", 1)
            if len(parts) == 2 and self._is_valid_field(parts[0], parts[1], w.value):
                validated.append(w)
        return validated

    # ---------- 降级 ----------

    @staticmethod
    def _fallback_proposal(text: str) -> CompileResult:
        """全失败 → 分类提案（未匹配文本摘要，category=其他）"""
        summary = text.strip()[:50] if text.strip() else "空输入"
        return CompileResult(
            classification_proposal=ClassificationProposal(
                suggestions=[Suggestion(field=summary, category="其他")]
            )
        )
