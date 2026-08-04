"""6维约束生成服务 — 权重查找 + prompt组装 + LLM生成。

Migrated from experiments/layered_weight_experiment.py with:
  - WeightMatrixLoader: YAML validation (8 scenarios)
  - DimensionPromptBuilder: system/user prompt migration
  - DimensionGenerator: LLM integration
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.ai.provider import LLMProvider
from app.config.paths import WEIGHT_MATRIX_PATH
from app.models.dimension import (
    DIMENSION_INFO,
    LAYER_NAMES,
    ConstraintDimension,
    CreationLayer,
    DimensionResultSet,
    WeightMatrix,
    WeightMatrixEntry,
    WeightMatrixError,
)

# ---------------------------------------------------------------------------
# WeightMatrixLoader
# ---------------------------------------------------------------------------

class WeightMatrixLoader:
    """Loads and validates weight_matrix.yaml with 8 validation scenarios.

    Validations:
        1. File existence
        2. YAML syntax
        3. Root is mapping
        4. All 6 layers present (no missing / no extra)
        5. Each layer has all 6 dimensions (no missing / no extra)
        6. Row sum == 100
        7. All values are int (not bool, not float)
        8. No negative values
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or WEIGHT_MATRIX_PATH

    def load(self) -> WeightMatrix:
        """Load YAML and validate. Raises WeightMatrixError on any failure."""

        # Validation 1: File missing
        if not self._path.exists():
            raise WeightMatrixError(row=None, detail=f"file not found: {self._path}")

        # Validation 2: YAML syntax error
        try:
            raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise WeightMatrixError(row=None, detail=f"yaml parse error: {e}") from e

        # Validation 3: Root must be a mapping
        if not isinstance(raw, dict):
            raise WeightMatrixError(row=None, detail="root must be a mapping")

        # Validation 4: Missing/extra layers
        expected_layers = {layer.value for layer in CreationLayer}
        actual_layers = set(raw.keys())
        missing = expected_layers - actual_layers
        if missing:
            raise WeightMatrixError(row=next(iter(missing)), detail="missing layer")
        extra = actual_layers - expected_layers
        if extra:
            raise WeightMatrixError(row=next(iter(extra)), detail="unexpected layer")

        # Build WeightMatrix, validating per-row
        entries: dict[str, WeightMatrixEntry] = {}
        for layer in CreationLayer:
            row_data = raw[layer.value]

            # Validation 5: Missing/extra dimensions per row
            expected_dims = {d.value for d in ConstraintDimension}
            actual_dims = set(row_data.keys()) if isinstance(row_data, dict) else set()
            missing_dim = expected_dims - actual_dims
            if missing_dim:
                raise WeightMatrixError(
                    row=layer.value, detail=f"missing dimension: {missing_dim}"
                )
            extra_dim = actual_dims - expected_dims
            if extra_dim:
                raise WeightMatrixError(
                    row=layer.value, detail=f"unexpected key: {extra_dim}"
                )

            # Validation 7: Non-integer values; Validation 8: Negative values
            for dim in ConstraintDimension:
                val = row_data[dim.value]
                if not isinstance(val, int) or isinstance(val, bool):
                    raise WeightMatrixError(
                        row=layer.value,
                        detail=f"non-integer weight for {dim.value}",
                    )
                if val < 0:
                    raise WeightMatrixError(
                        row=layer.value,
                        detail=f"negative weight for {dim.value}",
                    )

            # Validation 6: Row sum != 100
            row_sum = sum(row_data[d.value] for d in ConstraintDimension)
            if row_sum != 100:
                raise WeightMatrixError(
                    row=layer.value, detail=f"row sum is {row_sum}, expected 100"
                )

            entries[layer.value] = WeightMatrixEntry(**row_data)

        return WeightMatrix(**entries)

    def get_weights(self, layer: CreationLayer) -> WeightMatrixEntry:
        """Load matrix and return weights for a specific layer."""
        return self.load().get_entry(layer)


# ---------------------------------------------------------------------------
# DimensionPromptBuilder
# ---------------------------------------------------------------------------

class DimensionPromptBuilder:
    """Builds system/user prompts for 6-dimension constraint generation.

    Migrated exactly from experiments/layered_weight_experiment.py L172-272.
    """

    def build_system_prompt(
        self,
        layer: CreationLayer,
        weights: WeightMatrixEntry,
        intent: str,
    ) -> str:
        """构建 system prompt，包含权重表和创作意图。"""

        layer_name = LAYER_NAMES[layer]

        # 按权重降序排列维度
        weight_dict = weights.to_dict()
        sorted_dims = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)

        # 构建维度描述（按权重排序，高权重在前）
        dim_lines: list[str] = []
        for dim_code, weight in sorted_dims:
            info = DIMENSION_INFO[dim_code]
            bar = "█" * (weight // 5) + "░" * (20 - weight // 5)
            emphasis = ""
            if weight >= 25:
                emphasis = " ★主要约束"
            elif weight <= 5:
                emphasis = " （几乎不需要，简单提一句即可）"
            dim_lines.append(
                f"  {dim_code.value} ({info.name}) [{bar} {weight}%]{emphasis}\n"
                f"    → {info.desc}"
            )

        dims_text = "\n".join(dim_lines)

        return f"""\
你是一个分层创作系统中的世界构建引擎。

## 当前任务

DM 正在 **{layer_name}** 层创作。
创作意图: {intent}

## 这个层级的约束权重表

每一类约束在 {layer_name} 层的重要性不同。权重越高，你需要在生成内容中\
给予越多的篇幅和细节。标★的是主要约束，必须详细展开。低权重的维度\
可以简单提及甚至省略。

{dims_text}

## 生成原则

1. **按权重分配注意力** — 高权重维度的内容必须丰富、具体、有细节；低权重维度简略即可
2. **侧重差异要明显** — 如果换一个层级生成同样的种子，结果应该截然不同
3. **内容自洽** — 所有生成的维度内容必须围绕种子概念，逻辑一致
4. **具体可玩** — 不要泛泛而谈，给出具体的名称、数值、机制描述

## 输出格式

输出严格的 JSON，包含所有6个约束维度的内容。高权重维度字段内容丰富\
（多个子字段、列表、详细描述），低权重维度可以只有一句话或空列表。

```json
{{
  "RED": {{
    "forbidden": ["禁止的内容1", "禁止的内容2"],
    "note": "说明（如果没有禁忌可以留空列表）"
  }},
  "LAW": {{
    "rules": ["规则描述1", "规则描述2"],
    "mechanism": "核心运行机制描述"
  }},
  "ACT": {{
    "actions": [
      {{"trigger": "触发条件", "check": "判定方式", "success": "成功后果", "failure": "失败后果"}}
    ]
  }},
  "NAR": {{
    "style": "文风/氛围描述",
    "keywords": ["关键词1", "关键词2"],
    "tone": "基调（如：压抑/壮丽/诡异）"
  }},
  "WST": {{
    "effects": [
      {{"name": "效果名", "type": "buff/debuff/环境", "magnitude": "数值或描述"}}
    ]
  }},
  "SOC": {{
    "relations": [
      {{"target": "关系对象", "type": "关系类型", "value": "关系值/态度"}}
    ]
  }}
}}
```

只输出 JSON，不要输出任何其他内容。
"""

    def build_user_prompt(self, seed_input: str, seed_description: str) -> str:
        """构建 user prompt。"""
        return f"""\
## 种子概念

**名称**: {seed_input}
**描述**: {seed_description}

请根据上方权重表，在当前创作层级下生成这个种子的完整约束内容。
记住：高权重维度要详细，低权重维度要简略。
"""


# ---------------------------------------------------------------------------
# DimensionGenerator
# ---------------------------------------------------------------------------

class DimensionParseError(Exception):
    """LLM output parsing/validation failure."""

    def __init__(self, original: dict[str, Any], errors: Any = None) -> None:
        self.original = original
        self.errors = errors
        super().__init__(f"Failed to parse LLM output: {errors}")


class DimensionGenerator:
    """Core 6-dimension constraint generator using LLM."""

    def __init__(
        self,
        provider: LLMProvider,
        matrix_loader: WeightMatrixLoader | None = None,
    ) -> None:
        self._provider = provider
        self._loader = matrix_loader or WeightMatrixLoader()
        self._prompt_builder = DimensionPromptBuilder()

    async def generate(
        self,
        seed_input: str,
        seed_description: str,
        layer: CreationLayer,
        intent: str = "",
    ) -> DimensionResultSet:
        """Generate 6-dimension constraints for a seed at a specific layer."""
        weights = self._loader.get_weights(layer)
        system_prompt = self._prompt_builder.build_system_prompt(
            layer, weights, intent
        )
        user_prompt = self._prompt_builder.build_user_prompt(
            seed_input, seed_description
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self._provider.chat_json(messages)

        try:
            return DimensionResultSet.model_validate(raw)
        except Exception as e:
            raise DimensionParseError(original=raw, errors=str(e)) from e
