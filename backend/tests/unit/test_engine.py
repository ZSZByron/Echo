"""Unit tests for the deterministic rules engine."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.engine.god_intervention import apply_penalty, check_intervention
from app.engine.physics import (
    calculate_damage,
    calculate_energy_cost,
    check_strength_vs_hardness,
)
from app.engine.rules_engine import RulesEngine
from app.engine.world_loader import WorldLoader
from app.models.action import (
    ActionType,
    JudgmentOutcome,
    ParsedIntent,
)
from app.models.player import PlayerState, PlayerStatus
from app.models.world import GodKing

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


@pytest.fixture
def loader() -> WorldLoader:
    return WorldLoader(DATA_DIR)


@pytest.fixture
def engine(loader: WorldLoader) -> RulesEngine:
    return RulesEngine(loader)


@pytest.fixture
def default_player() -> PlayerState:
    return PlayerState(
        id="player_001",
        energy=80,
        health=90,
        strength=60,
        intelligence=70,
        echo_mode_enabled=False,
        mental_stability=85,
        location="temple_ruins",
        inventory=[],
        status=PlayerStatus.NORMAL,
        max_energy=100,
        max_health=100,
    )


def _make_intent(
    action_type: ActionType = ActionType.BRUTE_FORCE,
    target: str | None = None,
    intensity: str = "medium",
    risk_acceptance: bool = True,
    raw_input: str = "test action",
    confidence: float = 0.95,
) -> ParsedIntent:
    return ParsedIntent(
        action_type=action_type,
        target=target,
        intensity=intensity,  # type: ignore[arg-type]
        risk_acceptance=risk_acceptance,
        raw_input=raw_input,
        confidence=confidence,
    )


# ============================================================
# 1. Physics tests
# ============================================================


class TestPhysics:
    def test_strength_less_than_hardness_fails(self) -> None:
        assert check_strength_vs_hardness(50, 75) is False

    def test_strength_equal_hardness_succeeds(self) -> None:
        assert check_strength_vs_hardness(75, 75) is True

    def test_strength_greater_hardness_succeeds(self) -> None:
        assert check_strength_vs_hardness(80, 75) is True

    def test_damage_minimum_zero(self) -> None:
        assert calculate_damage(5, 10) == 0

    def test_damage_positive(self) -> None:
        assert calculate_damage(30, 10) == 20

    def test_energy_cost_low(self) -> None:
        assert calculate_energy_cost(20, "low") == 10

    def test_energy_cost_medium(self) -> None:
        assert calculate_energy_cost(20, "medium") == 20

    def test_energy_cost_maximum(self) -> None:
        assert calculate_energy_cost(20, "maximum") == 30

    def test_energy_cost_unknown_intensity(self) -> None:
        assert calculate_energy_cost(20, "unknown") == 20


# ============================================================
# 2. God intervention tests
# ============================================================


class TestGodIntervention:
    def test_no_intervention_unprotected_target(self, loader: WorldLoader) -> None:
        gods = loader.load_gods()
        table = loader.load_intervention_table()
        result = check_intervention("nonexistent_object", table, gods)
        assert result is None

    def test_intervention_protected_anchor(self, loader: WorldLoader) -> None:
        gods = loader.load_gods()
        table = loader.load_intervention_table()
        result = check_intervention("ancient_locked_door", table, gods)
        assert result is not None
        assert result.id == "chronos_order"

    def test_intervention_empty_target(self, loader: WorldLoader) -> None:
        gods = loader.load_gods()
        table = loader.load_intervention_table()
        result = check_intervention("", table, gods)
        assert result is None

    def test_apply_penalty_returns_two_changes(self) -> None:
        god = GodKing(
            id="test_god",
            name="Test",
            domain="Testing",
            intervention_threshold=50,
            penalty=40,
        )
        changes = apply_penalty(god, "p1")
        assert len(changes) == 2
        assert changes[0].property_name == "health"
        assert changes[0].new_value == 40
        assert changes[1].property_name == "mental_stability"
        assert changes[1].new_value == 20


# ============================================================
# 3. Rules engine integration tests
# ============================================================


class TestRulesEngine:
    async def test_brute_force_fail_insufficient_strength(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="ancient_locked_door",
            intensity="maximum",
            raw_input="I smash the door",
        )
        result = await engine.judge(intent, default_player)
        # ancient_locked_door is anchor + protected => forced_fail
        assert result.result == JudgmentOutcome.FORCED_FAIL
        assert result.god_intervention == "Chronos the Order"
        assert result.damage == 40

    async def test_brute_force_non_anchor_success(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="priest_corpse_01",
            raw_input="I search the corpse",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS
        assert "60 >= 10" in result.reason

    async def test_god_intervention_anchor(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="holographic_altar",
            raw_input="I destroy the altar",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.FORCED_FAIL
        assert result.god_intervention == "Mnemosyne the Weaver"
        assert result.damage == 25

    async def test_no_target_success(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target=None,
            raw_input="I look around",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS
        assert "无特定目标" in result.reason

    async def test_unknown_target_treated_as_no_target(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="nonexistent_thing",
            raw_input="I touch the wall",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS

    async def test_empty_string_target(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="",
            raw_input="I wait",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS


# ============================================================
# 4. All 7 ActionTypes
# ============================================================


@pytest.mark.parametrize(
    "action_type",
    [
        ActionType.BRUTE_FORCE,
        ActionType.STEALTH,
        ActionType.READ_MEMORY,
        ActionType.NEGOTIATE,
        ActionType.PROBE,
        ActionType.GOD_PROVOKE,
        ActionType.INVESTIGATE,
    ],
)
class TestAllActionTypes:
    async def test_action_type_no_target(
        self,
        engine: RulesEngine,
        default_player: PlayerState,
        action_type: ActionType,
    ) -> None:
        intent = _make_intent(
            action_type=action_type,
            target=None,
            raw_input=f"Doing {action_type.value}",
        )
        result = await engine.judge(intent, default_player)
        assert result.result in (JudgmentOutcome.SUCCESS,)


# ============================================================
# 5. Determinism: same input 100x => identical output
# ============================================================


class TestDeterminism:
    async def test_100_identical_results(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="neon_circuit_pillar",
            intensity="maximum",
            raw_input="I smash the pillar",
        )
        first = await engine.judge(intent, default_player)
        first_json = first.model_dump_json()

        for _ in range(99):
            result = await engine.judge(intent, default_player)
            assert result.model_dump_json() == first_json

    async def test_100_identical_intervention_results(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="ancient_locked_door",
            intensity="maximum",
            raw_input="I force the ancient door",
        )
        first = await engine.judge(intent, default_player)
        first_json = first.model_dump_json()

        for _ in range(99):
            result = await engine.judge(intent, default_player)
            assert result.model_dump_json() == first_json


# ============================================================
# 6. Energy cost integration
# ============================================================


class TestEnergyCostIntegration:
    async def test_low_intensity_energy(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="priest_corpse_01",
            intensity="low",
            raw_input="Gently search",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS

    async def test_maximum_intensity_energy(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="priest_corpse_01",
            intensity="maximum",
            raw_input="Violently search",
        )
        result = await engine.judge(intent, default_player)
        assert result.result == JudgmentOutcome.SUCCESS


# ============================================================
# 7. NarrativeContext verification
# ============================================================


class TestNarrativeContext:
    async def test_scene_id_populated(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(target=None, raw_input="look")
        result = await engine.judge(intent, default_player)
        assert result.narrative_context.scene_id == "temple_ruins"

    async def test_god_intervention_tension_80(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="ancient_locked_door", raw_input="smash"
        )
        result = await engine.judge(intent, default_player)
        assert result.narrative_context.tension_level == 80
        assert "Chronos the Order" in result.narrative_context.active_gods

    async def test_no_intervention_tension_50(
        self, engine: RulesEngine, default_player: PlayerState
    ) -> None:
        intent = _make_intent(
            target="priest_corpse_01", raw_input="search"
        )
        result = await engine.judge(intent, default_player)
        assert result.narrative_context.tension_level == 50


# ============================================================
# 8. WorldLoader tests
# ============================================================


class TestWorldLoader:
    def test_load_scene(self, loader: WorldLoader) -> None:
        scene = loader.load_scene("temple_ruins")
        assert scene.scene_id == "temple_ruins"
        assert len(scene.accessible_objects) == 7

    def test_load_gods(self, loader: WorldLoader) -> None:
        gods = loader.load_gods()
        assert len(gods) == 5
        assert gods[0].id == "chronos_order"

    def test_load_intervention_table(self, loader: WorldLoader) -> None:
        table = loader.load_intervention_table()
        assert table["ancient_locked_door"] == "chronos_order"
        assert table["holographic_altar"] == "mnemosyne_memory"

    def test_load_default_player(self, loader: WorldLoader) -> None:
        data = loader.load_default_player_data()
        assert data["id"] == "player_001"
        assert data["strength"] == 60
