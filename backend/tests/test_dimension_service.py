"""Tests for dimension_generator.py — WeightMatrixLoader, DimensionPromptBuilder, DimensionGenerator.

13 test cases, no real LLM calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.ai.provider import LLMProvider
from app.models.dimension import (
    ConstraintDimension,
    CreationLayer,
    DimensionResultSet,
    WeightMatrixEntry,
    WeightMatrixError,
)
from app.domains.creation.constraint.dimension_generator import (
    DimensionGenerator,
    DimensionParseError,
    DimensionPromptBuilder,
    WeightMatrixLoader,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_MATRIX_YAML = """\
world:
  RED: 20
  LAW: 30
  ACT: 5
  NAR: 35
  WST: 5
  SOC: 5
region:
  RED: 10
  LAW: 10
  ACT: 10
  NAR: 20
  WST: 5
  SOC: 45
scene:
  RED: 10
  LAW: 25
  ACT: 5
  NAR: 10
  WST: 40
  SOC: 10
campaign:
  RED: 10
  LAW: 5
  ACT: 10
  NAR: 40
  WST: 5
  SOC: 30
npc:
  RED: 5
  LAW: 10
  ACT: 25
  NAR: 20
  WST: 10
  SOC: 30
asset:
  RED: 10
  LAW: 30
  ACT: 30
  NAR: 10
  WST: 10
  SOC: 10
"""


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return "mock"

    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        return self._response


VALID_LLM_RESPONSE = {
    "RED": {"forbidden": ["暴力内容"], "note": "禁止过度血腥"},
    "LAW": {"rules": ["魔法消耗理智"], "mechanism": "施法时理智值下降"},
    "ACT": {"actions": [{"trigger": "施法", "check": "理智检定", "success": "法术生效", "failure": "陷入疯狂"}]},
    "NAR": {"style": "暗黑哥特", "keywords": ["神秘", "压抑"], "tone": "压抑"},
    "WST": {"effects": [{"name": "魔力场", "type": "环境", "magnitude": "强"}]},
    "SOC": {"relations": [{"target": "教廷", "type": "敌对", "value": "-50"}]},
}


def _write_valid_matrix(path: Path) -> None:
    path.write_text(VALID_MATRIX_YAML, encoding="utf-8")


# ===========================================================================
# WeightMatrixLoader tests (7)
# ===========================================================================


class TestWeightMatrixLoader:

    def test_weight_matrix_loads_successfully(self, tmp_path: Path) -> None:
        """Loads valid weight_matrix.yaml, asserts 6 layers, each row sum=100."""
        p = tmp_path / "weight_matrix.yaml"
        _write_valid_matrix(p)
        loader = WeightMatrixLoader(path=p)
        matrix = loader.load()

        # All 6 layers present
        for layer in CreationLayer:
            entry = matrix.get_entry(layer)
            assert isinstance(entry, WeightMatrixEntry)
            assert entry.sum() == 100

    def test_weight_matrix_missing_file_raises(self, tmp_path: Path) -> None:
        """Point to nonexistent path → WeightMatrixError."""
        loader = WeightMatrixLoader(path=tmp_path / "nonexistent.yaml")
        with pytest.raises(WeightMatrixError, match="file not found"):
            loader.load()

    def test_weight_matrix_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Write temp file with invalid YAML → WeightMatrixError."""
        p = tmp_path / "bad.yaml"
        p.write_text("{not valid", encoding="utf-8")
        loader = WeightMatrixLoader(path=p)
        with pytest.raises(WeightMatrixError, match="yaml parse error"):
            loader.load()

    def test_weight_matrix_row_sum_not_100_raises(self, tmp_path: Path) -> None:
        """Temp YAML with a row summing to 99 → WeightMatrixError."""
        p = tmp_path / "bad_sum.yaml"
        yaml_content = VALID_MATRIX_YAML.replace("RED: 20", "RED: 19", 1)
        p.write_text(yaml_content, encoding="utf-8")
        loader = WeightMatrixLoader(path=p)
        with pytest.raises(WeightMatrixError, match="row sum is 99"):
            loader.load()

    def test_weight_matrix_negative_value_raises(self, tmp_path: Path) -> None:
        """Temp YAML with -1 → WeightMatrixError."""
        p = tmp_path / "negative.yaml"
        yaml_content = VALID_MATRIX_YAML.replace("RED: 20", "RED: -1", 1)
        p.write_text(yaml_content, encoding="utf-8")
        loader = WeightMatrixLoader(path=p)
        with pytest.raises(WeightMatrixError, match="negative weight"):
            loader.load()

    def test_weight_matrix_missing_layer_raises(self, tmp_path: Path) -> None:
        """Temp YAML with only 5 layers → WeightMatrixError."""
        p = tmp_path / "missing_layer.yaml"
        # Remove the npc block
        lines = VALID_MATRIX_YAML.strip().split("\n")
        filtered = []
        in_npc = False
        for line in lines:
            if line.startswith("npc:"):
                in_npc = True
            if not in_npc:
                filtered.append(line)
            if in_npc and line and not line.startswith(" "):
                in_npc = False
        p.write_text("\n".join(filtered), encoding="utf-8")
        loader = WeightMatrixLoader(path=p)
        with pytest.raises(WeightMatrixError, match="missing layer"):
            loader.load()

    def test_weight_matrix_missing_dimension_raises(self, tmp_path: Path) -> None:
        """Temp YAML with a row having only 5 dims → WeightMatrixError."""
        p = tmp_path / "missing_dim.yaml"
        # Remove NAR from the world row
        yaml_content = VALID_MATRIX_YAML
        lines = yaml_content.strip().split("\n")
        filtered = []
        skip_nar = False
        for line in lines:
            if line.strip().startswith("NAR:") and not any(
                l.strip().startswith(("world:", "region:", "scene:", "campaign:", "npc:", "asset:"))
                for l in [lines[lines.index(line) - 1]] if lines.index(line) > 0
            ):
                # Skip this NAR line only if we're in the first layer block (world)
                pass
            filtered.append(line)
        # Simpler approach: just remove the NAR line from world block
        world_block_end = yaml_content.index("region:")
        world_block = yaml_content[:world_block_end]
        modified_world = "\n".join(
            l for l in world_block.split("\n") if not l.strip().startswith("NAR:")
        )
        final = modified_world + yaml_content[world_block_end:]
        p.write_text(final, encoding="utf-8")
        loader = WeightMatrixLoader(path=p)
        with pytest.raises(WeightMatrixError, match="missing dimension"):
            loader.load()


# ===========================================================================
# DimensionPromptBuilder tests (3)
# ===========================================================================


class TestDimensionPromptBuilder:

    def _make_weights(self, **overrides: int) -> WeightMatrixEntry:
        defaults = {"RED": 20, "LAW": 30, "ACT": 5, "NAR": 35, "WST": 5, "SOC": 5}
        defaults.update(overrides)
        # Re-normalize to sum=100 to pass Pydantic validation
        total = sum(defaults.values())
        if total != 100:
            diff = 100 - total
            defaults["NAR"] = defaults.get("NAR", 0) + diff
        return WeightMatrixEntry(**defaults)

    def test_build_system_prompt_includes_all_dimensions(self) -> None:
        """Mock weights, assert prompt contains all 6 dimension names."""
        builder = DimensionPromptBuilder()
        weights = self._make_weights()
        prompt = builder.build_system_prompt(
            CreationLayer.WORLD, weights, "测试意图"
        )
        for dim in ConstraintDimension:
            info = __import__(
                "app.models.dimension", fromlist=["DIMENSION_INFO"]
            ).DIMENSION_INFO[dim]
            assert info.name in prompt, f"Missing dimension name: {info.name}"

    def test_build_system_prompt_high_weight_marked(self) -> None:
        """Assert weight>=25% dimension has ★ marker."""
        builder = DimensionPromptBuilder()
        weights = self._make_weights(NAR=35)
        prompt = builder.build_system_prompt(
            CreationLayer.WORLD, weights, ""
        )
        assert "★主要约束" in prompt

    def test_build_system_prompt_low_weight_simplified(self) -> None:
        """Assert weight<=5% dimension has '简单提一句' text."""
        builder = DimensionPromptBuilder()
        weights = self._make_weights(ACT=5)
        prompt = builder.build_system_prompt(
            CreationLayer.WORLD, weights, ""
        )
        assert "简单提一句" in prompt


# ===========================================================================
# DimensionGenerator tests (3)
# ===========================================================================


class TestDimensionGenerator:

    @pytest.mark.asyncio
    async def test_generate_parses_llm_response(self, tmp_path: Path) -> None:
        """Mock provider returns valid 6-dim JSON → returns DimensionResultSet."""
        p = tmp_path / "weight_matrix.yaml"
        _write_valid_matrix(p)

        provider = MockProvider(VALID_LLM_RESPONSE)
        loader = WeightMatrixLoader(path=p)
        gen = DimensionGenerator(provider=provider, matrix_loader=loader)

        result = await gen.generate(
            seed_input="魔法消耗理智值",
            seed_description="每次施放法术理智下降",
            layer=CreationLayer.WORLD,
            intent="定义世界法则",
        )
        assert isinstance(result, DimensionResultSet)
        assert result.LAW.mechanism == "施法时理智值下降"
        assert len(result.RED.forbidden) == 1

    @pytest.mark.asyncio
    async def test_generate_invalid_llm_output_raises(self, tmp_path: Path) -> None:
        """Mock provider returns invalid structure → raises DimensionParseError."""
        p = tmp_path / "weight_matrix.yaml"
        _write_valid_matrix(p)

        # DimensionResultSet uses model_validate(dict); pass a non-dict to trigger failure.
        # Since chat_json returns dict, we pass a dict with wrong types that Pydantic rejects.
        invalid_response = {"RED": "not_a_list"}  # forbidden should be list[str], not str
        provider = MockProvider(invalid_response)
        loader = WeightMatrixLoader(path=p)
        gen = DimensionGenerator(provider=provider, matrix_loader=loader)

        with pytest.raises(DimensionParseError):
            await gen.generate(
                seed_input="测试",
                seed_description="测试描述",
                layer=CreationLayer.WORLD,
            )

    def test_build_user_prompt_contains_seed(self) -> None:
        """Assert user prompt contains seed_input and seed_description."""
        builder = DimensionPromptBuilder()
        prompt = builder.build_user_prompt("古代水晶祭坛", "水晶祭坛发光")
        assert "古代水晶祭坛" in prompt
        assert "水晶祭坛发光" in prompt
