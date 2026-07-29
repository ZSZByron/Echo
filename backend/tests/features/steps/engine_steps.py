"""Gherkin step implementations for engine feature tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from behave import given, then, when  # type: ignore[import]

from app.engine.rules_engine import RulesEngine
from app.engine.world_loader import WorldLoader
from app.models.action import ActionType, ParsedIntent
from app.models.player import PlayerState, PlayerStatus

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data"


def _build_player(strength: int) -> PlayerState:
    return PlayerState(
        id="player_001",
        energy=80,
        health=90,
        strength=strength,
        intelligence=70,
        echo_mode_enabled=False,
        mental_stability=85,
        location="temple_ruins",
        inventory=[],
        status=PlayerStatus.NORMAL,
        max_energy=100,
        max_health=100,
    )


def _build_intent(
    action_type: ActionType,
    target: str | None,
) -> ParsedIntent:
    return ParsedIntent(
        action_type=action_type,
        target=target,
        intensity="medium",
        risk_acceptance=True,
        raw_input="test action",
        confidence=0.95,
    )


@given("the player has strength {strength:d}")
def step_player_strength(context: object, strength: int) -> None:
    context.player = _build_player(strength)  # type: ignore[attr-defined]
    loader = WorldLoader(DATA_DIR)
    context.engine = RulesEngine(loader)  # type: ignore[attr-defined]


@given('the player targets "{target_id}" with {action}')
def step_player_targets(context: object, target_id: str, action: str) -> None:
    action_map: dict[str, ActionType] = {
        "brute_force": ActionType.BRUTE_FORCE,
        "stealth": ActionType.STEALTH,
        "read_memory": ActionType.READ_MEMORY,
        "negotiate": ActionType.NEGOTIATE,
        "probe": ActionType.PROBE,
        "god_provoke": ActionType.GOD_PROVOKE,
        "investigate": ActionType.INVESTIGATE,
    }
    context.intent = _build_intent(action_map[action], target_id)  # type: ignore[attr-defined]


@given("the player has no specific target with {action}")
def step_no_target(context: object, action: str) -> None:
    action_map: dict[str, ActionType] = {
        "brute_force": ActionType.BRUTE_FORCE,
        "stealth": ActionType.STEALTH,
        "read_memory": ActionType.READ_MEMORY,
        "negotiate": ActionType.NEGOTIATE,
        "probe": ActionType.PROBE,
        "god_provoke": ActionType.GOD_PROVOKE,
        "investigate": ActionType.INVESTIGATE,
    }
    context.intent = _build_intent(action_map[action], None)  # type: ignore[attr-defined]


@when("the rules engine judges the action")
async def step_judge(context: object) -> None:
    engine: RulesEngine = context.engine  # type: ignore[attr-defined]
    intent: ParsedIntent = context.intent  # type: ignore[attr-defined]
    player: PlayerState = context.player  # type: ignore[attr-defined]
    context.result = await engine.judge(intent, player)  # type: ignore[attr-defined]


@when("the rules engine judges the action {count:d} times")
async def step_judge_multiple(context: object, count: int) -> None:
    engine: RulesEngine = context.engine  # type: ignore[attr-defined]
    intent: ParsedIntent = context.intent  # type: ignore[attr-defined]
    player: PlayerState = context.player  # type: ignore[attr-defined]
    context.results: list = []  # type: ignore[attr-defined]
    for _ in range(count):
        r = await engine.judge(intent, player)
        context.results.append(r.model_dump_json())


@then("the result is {outcome}")
def step_check_outcome(context: object, outcome: str) -> None:
    result = context.result  # type: ignore[attr-defined]
    assert result.result.value == outcome, (  # type: ignore[attr-defined]
        f"Expected {outcome}, got {result.result.value}"
    )


@then('god "{god_name}" intervened')
def step_check_god(context: object, god_name: str) -> None:
    result = context.result  # type: ignore[attr-defined]
    assert result.god_intervention == god_name, (  # type: ignore[attr-defined]
        f"Expected god {god_name}, got {result.god_intervention}"
    )


@then("no god intervened")
def step_no_god(context: object) -> None:
    result = context.result  # type: ignore[attr-defined]
    assert result.god_intervention is None  # type: ignore[attr-defined]


@then("the damage is {damage:d}")
def step_check_damage(context: object, damage: int) -> None:
    result = context.result  # type: ignore[attr-defined]
    assert result.damage == damage  # type: ignore[attr-defined]


@then("all {count:d} results are identical")
def step_check_determinism(context: object, count: int) -> None:
    results: list[str] = context.results  # type: ignore[attr-defined]
    assert len(results) == count
    assert len(set(results)) == 1, f"Got {len(set(results))} unique results"


@then('the reason contains "{text}"')
def step_check_reason(context: object, text: str) -> None:
    result = context.result  # type: ignore[attr-defined]
    assert text in result.reason  # type: ignore[attr-defined]
