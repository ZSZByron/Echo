"""Unit tests for constraint application tree (breakpoint C).

Validates the 6-dim x 6-layer injection mapping table:
- YAML loading
- get_injections(layer) query + priority ordering
- Completeness: exactly 36 rules, 6 dims x 6 layers, no dup/gap
- target_node_field legality vs real GraphNode/GraphEdge fields
- target_prompt_layer legality vs PromptBuilder 8 layers
- Error path on missing dimension
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.domains.creation.constraint.application_tree import (
    DIMENSIONS,
    LAYERS,
    PROMPT_LAYERS,
    ApplicationTreeLoader,
    InjectionRule,
)
from app.models.knowledge_graph import GraphEdge, GraphNode


@pytest.fixture(scope="module")
def loader() -> ApplicationTreeLoader:
    return ApplicationTreeLoader()


class TestYamlLoading:
    def test_load_returns_36_rules(self, loader: ApplicationTreeLoader) -> None:
        rules = loader.get_all_rules()
        assert len(rules) == 36
        assert all(isinstance(r, InjectionRule) for r in rules)

    def test_injection_rule_has_six_fields(self, loader: ApplicationTreeLoader) -> None:
        rule = loader.get_all_rules()[0]
        for field in (
            "source_field",
            "target_prompt_layer",
            "target_node_field",
            "target_edge_type",
            "transform",
            "priority",
        ):
            assert field in InjectionRule.model_fields


class TestGetInjections:
    def test_returns_layer_rules_sorted_by_priority(
        self, loader: ApplicationTreeLoader
    ) -> None:
        rules = loader.get_injections("world")
        assert len(rules) == 6
        priorities = [r.priority for r in rules]
        assert priorities == sorted(priorities)

    def test_unknown_layer_raises(self, loader: ApplicationTreeLoader) -> None:
        with pytest.raises(ValueError):
            loader.get_injections("galaxy")


class TestCompleteness:
    def test_all_dim_layer_pairs_present_exactly_once(
        self, loader: ApplicationTreeLoader
    ) -> None:
        rules = loader.get_all_rules()
        pairs = [(r.dimension, r.layer) for r in rules]
        assert len(pairs) == len(set(pairs)) == 36
        for dim in DIMENSIONS:
            for layer in LAYERS:
                assert (dim, layer) in set(pairs), f"missing {dim} x {layer}"


class TestFieldLegality:
    def test_target_node_fields_exist_in_graph_models(
        self, loader: ApplicationTreeLoader
    ) -> None:
        legal = set(GraphNode.model_fields) | set(GraphEdge.model_fields)
        for rule in loader.get_all_rules():
            assert rule.target_node_field in legal, (
                f"{rule.dimension}.{rule.layer}: illegal node field "
                f"{rule.target_node_field!r}"
            )

    def test_target_prompt_layers_in_prompt_builder_set(
        self, loader: ApplicationTreeLoader
    ) -> None:
        for rule in loader.get_all_rules():
            assert rule.target_prompt_layer in PROMPT_LAYERS


class TestLawExamples:
    """LAW WORLD rule mirrors hierarchy-diagram breakpoint C example."""

    def test_law_world_structure_world_rule(self, loader: ApplicationTreeLoader) -> None:
        rule = loader.get_injections("world")[0]
        assert rule.source_field == "LAW.world_structure"
        assert rule.target_prompt_layer == "world"
        assert rule.target_edge_type == "RULE_SHAPES_GEO"
        assert rule.transform == "map_to_vertical_layer_enum"
        assert rule.priority == 1

    def test_law_world_structure_varies_by_layer(
        self, loader: ApplicationTreeLoader
    ) -> None:
        """Same LAW field targets different prompt layers per hierarchy diagram."""
        targets = {
            r.layer: r.target_prompt_layer
            for r in loader.get_all_rules()
            if r.source_field == "LAW.world_structure"
        }
        assert targets["world"] == "world"
        assert targets["scene"] == "location"
        assert targets["npc"] == "subject"
        assert targets["asset"] == "material"


class TestErrorPaths:
    def test_missing_dimension_raises(self, tmp_path) -> None:
        import yaml

        data = yaml.safe_load(
            (ApplicationTreeLoader().path).read_text(encoding="utf-8")
        )
        for layer_rules in data.values():
            layer_rules[:] = [
                r for r in layer_rules if not r["source_field"].startswith("SOC.")
            ]
        bad = tmp_path / "bad_tree.yaml"
        bad.write_text(yaml.dump(data), encoding="utf-8")
        with pytest.raises(ValueError, match="SOC"):
            ApplicationTreeLoader(path=bad)


class TestModelContract:
    def test_injection_rule_is_pydantic_v2(self) -> None:
        assert issubclass(InjectionRule, BaseModel)
        assert hasattr(InjectionRule, "model_validate")
