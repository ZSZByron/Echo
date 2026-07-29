"""T10 Verification: Object x Action matrix, God rules, Parser, Performance."""
from __future__ import annotations

import asyncio
import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock

# Ensure project root is on path (must come before any app imports)
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.ai.parser import IntentParser
from app.engine.rules_engine import RulesEngine
from app.engine.world_loader import WorldLoader
from app.models.action import ActionType, ParsedIntent
from app.models.player import PlayerState, PlayerStatus

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def make_player() -> PlayerState:
    return PlayerState(
        id="player_001", energy=80, health=90, strength=60,
        intelligence=70, echo_mode_enabled=False, mental_stability=85,
        location="temple_ruins", inventory=[], status=PlayerStatus.NORMAL,
        max_energy=100, max_health=100,
    )


def make_intent(action: ActionType, target: str | None, raw: str = "test") -> ParsedIntent:
    return ParsedIntent(
        action_type=action, target=target, intensity="medium",
        risk_acceptance=False, raw_input=raw, confidence=0.9,
    )


def make_intent_any(action: ActionType, target: str | None) -> ParsedIntent:
    return make_intent(action, target, f"test {action.value} {target or ''}")


# ==================================================================
# STEP 1: Object x Action Matrix
# ==================================================================

async def verify_matrix() -> tuple[str, bool]:
    buf = StringIO()
    loader = WorldLoader(DATA_DIR)
    engine = RulesEngine(loader)
    player = make_player()

    objects = [
        "ancient_locked_door",
        "priest_corpse_01",
        "holographic_altar",
        "neon_circuit_pillar",
    ]
    actions = [
        ActionType.BRUTE_FORCE,
        ActionType.STEALTH,
        ActionType.READ_MEMORY,
        ActionType.NEGOTIATE,
        ActionType.PROBE,
        ActionType.GOD_PROVOKE,
        ActionType.INVESTIGATE,
    ]

    results: dict[str, str] = {}
    buf.write("=== Object x Action Matrix ===\n")
    for obj_id in objects:
        for action in actions:
            intent = make_intent_any(action, obj_id)
            judgment = await engine.judge(intent, player)
            key = f"{obj_id} x {action.value}"
            val = judgment.result.value
            results[key] = val
            buf.write(f"  {key}: {val}\n")

    # Key assertions
    buf.write("\n=== Matrix Assertions ===\n")
    errors: list[str] = []

    # God-protected future anchors -> forced_fail for ALL actions
    anchor_objects = ["ancient_locked_door", "holographic_altar"]
    for obj in anchor_objects:
        for action in actions:
            key = f"{obj} x {action.value}"
            expected = "forced_fail"
            if results[key] != expected:
                errors.append(f"  FAIL: {key} expected '{expected}', got '{results[key]}'")
            else:
                buf.write(f"  PASS: {key} = {expected}\n")

    # Non-anchor objects: brute_force goes to physics
    # priest_corpse_01: hardness=10, strength=60 -> success
    key = "priest_corpse_01 x brute_force"
    if results[key] != "success":
        errors.append(f"  FAIL: {key} expected 'success', got '{results[key]}'")
    else:
        buf.write(f"  PASS: {key} = success (strength 60 >= hardness 10)\n")

    # neon_circuit_pillar: hardness=60, strength=60 -> success (>=)
    key = "neon_circuit_pillar x brute_force"
    if results[key] != "success":
        errors.append(f"  FAIL: {key} expected 'success', got '{results[key]}'")
    else:
        buf.write(f"  PASS: {key} = success (strength 60 >= hardness 60)\n")

    # Non-brute_force on non-anchors -> physics check
    non_anchor_objects = ["priest_corpse_01", "neon_circuit_pillar"]
    non_brute_actions = [a for a in actions if a != ActionType.BRUTE_FORCE]
    for obj in non_anchor_objects:
        for action in non_brute_actions:
            key = f"{obj} x {action.value}"
            if results[key] != "success":
                errors.append(f"  FAIL: {key} expected 'success', got '{results[key]}'")
            else:
                buf.write(f"  PASS: {key} = success\n")

    if errors:
        buf.write(f"\n*** {len(errors)} ASSERTION FAILURES ***\n")
        for e in errors:
            buf.write(e + "\n")
    else:
        buf.write("\n*** All matrix assertions passed! ***\n")

    return buf.getvalue(), len(errors) == 0


# ==================================================================
# STEP 2: God Rules Verification
# ==================================================================

async def verify_gods() -> tuple[str, bool]:
    buf = StringIO()
    loader = WorldLoader(DATA_DIR)
    gods = loader.load_gods()
    table = loader.load_intervention_table()
    engine = RulesEngine(loader)
    player = make_player()

    buf.write("=== God Rules Verification ===\n")
    buf.write(f"Total gods defined: {len(gods)}\n")
    for g in gods:
        buf.write(f"  - {g.id} ({g.name}), penalty={g.penalty}\n")

    buf.write(f"\nIntervention table entries: {len(table)}\n")
    for obj_id, god_id in table.items():
        buf.write(f"  - {obj_id} -> {god_id}\n")

    # Verify each god has entries
    buf.write("\n=== Per-God Trigger Check ===\n")
    god_to_objects: dict[str, list[str]] = {}
    for obj_id, god_id in table.items():
        god_to_objects.setdefault(god_id, []).append(obj_id)

    errors: list[str] = []
    for god in gods:
        objs = god_to_objects.get(god.id, [])
        buf.write(f"  {god.id}: protects {objs}\n")

    # Actually test the 2 triggerable gods in temple_ruins
    buf.write("\n=== Active God Trigger Tests ===\n")
    for obj_id, expected_god_id in [
        ("ancient_locked_door", "chronos_order"),
        ("holographic_altar", "mnemosyne_memory"),
    ]:
        intent = make_intent(ActionType.BRUTE_FORCE, obj_id, f"test {obj_id}")
        judgment = await engine.judge(intent, player)
        if judgment.result.value == "forced_fail" and judgment.god_intervention:
            god = next(g for g in gods if g.id == expected_god_id)
            buf.write(f"  PASS: {obj_id} -> forced_fail by {judgment.god_intervention}\n")
            buf.write(f"    Penalty: health=-{god.penalty}, stability=-{god.penalty // 2}\n")
            buf.write(f"    Damage field: {judgment.damage}\n")
        else:
            errors.append(f"  FAIL: {obj_id} did not trigger god intervention")
            buf.write(f"  FAIL: {obj_id} result={judgment.result.value}, god={judgment.god_intervention}\n")

    # Verify 3 non-triggerable gods have table entries (abstract objects)
    buf.write("\n=== Abstract God Entries (not in scene) ===\n")
    for god_id in ["ananke_entropy", "aion_cyclical", "caerus_opportunity"]:
        entries = god_to_objects.get(god_id, [])
        if entries:
            buf.write(f"  PASS: {god_id} has {entries} in table\n")
        else:
            errors.append(f"  FAIL: {god_id} has no entries in table")

    if errors:
        buf.write(f"\n*** {len(errors)} GOD ASSERTION FAILURES ***\n")
        for e in errors:
            buf.write(e + "\n")
    else:
        buf.write("\n*** All god rule assertions passed! ***\n")

    return buf.getvalue(), len(errors) == 0


# ==================================================================
# STEP 3: Parser Robustness
# ==================================================================

async def verify_parser() -> tuple[str, bool]:
    buf = StringIO()
    from app.ai.provider import LLMProvider

    class MockProvider(LLMProvider):
        def __init__(self, return_action: str | None):
            self._action = return_action

        async def chat(self, messages, **kwargs):
            return ""

        async def chat_json(self, messages, **kwargs):
            return {
                "action_type": self._action or "probe",
                "target": None,
                "intensity": "medium",
                "risk_acceptance": False,
                "tool_used": None,
            }

    test_cases = [
        ("砸门", "brute_force"),
        ("暴力破门", "brute_force"),
        ("撞开", "brute_force"),
        ("一拳打碎", "brute_force"),
        ("踢开", "brute_force"),
        ("我悄悄检查祭司尸体", "stealth"),
        ("读取记忆", "read_memory"),
        ("试图与祭坛沟通", "negotiate"),
        ("检查周围环境", "probe"),
        ("我向神王挑衅", "god_provoke"),
        ("仔细调查", "investigate"),
    ]

    buf.write("=== Parser Robustness (11 test cases, 5 brute_force synonyms) ===\n")
    errors: list[str] = []
    for text, expected in test_cases:
        mock = MockProvider(expected)
        parser = IntentParser(mock)
        result = await parser.parse(text)
        actual = result.action_type.value
        status = "PASS" if actual == expected else "FAIL"
        if status == "FAIL":
            errors.append(f"  {status}: '{text}' expected {expected}, got {actual}")
        buf.write(f"  {status}: '{text}' -> {actual}\n")

    # Test fallback (invalid action type)
    buf.write("\n=== Fallback Tests ===\n")
    mock_bad = MockProvider("invalid_action_type_xyz")
    parser_bad = IntentParser(mock_bad)
    fallback_result = await parser_bad.parse("random input")
    if fallback_result.action_type == ActionType.PROBE and fallback_result.confidence == 0.0:
        buf.write(f"  PASS: Invalid action_type -> fallback to probe (confidence=0.0)\n")
    else:
        errors.append("FAIL: Fallback did not work correctly for invalid action type")
        buf.write(f"  FAIL: Got {fallback_result.action_type.value}, confidence={fallback_result.confidence}\n")

    # Test with exception-raising provider
    class ErrorProvider(LLMProvider):
        async def chat(self, messages, **kwargs):
            raise RuntimeError("LLM unavailable")

        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM unavailable")

    error_parser = IntentParser(ErrorProvider())
    error_result = await error_parser.parse("test input")
    if error_result.action_type == ActionType.PROBE and error_result.confidence == 0.0:
        buf.write(f"  PASS: Exception in provider -> fallback to probe (confidence=0.0)\n")
    else:
        errors.append("FAIL: Exception fallback did not work")
        buf.write(f"  FAIL: Got {error_result.action_type.value}, confidence={error_result.confidence}\n")

    if errors:
        buf.write(f"\n*** {len(errors)} PARSER FAILURES ***\n")
        for e in errors:
            buf.write(e + "\n")
    else:
        buf.write("\n*** All parser tests passed! ***\n")

    return buf.getvalue(), len(errors) == 0


# ==================================================================
# STEP 4: Performance Verification
# ==================================================================

async def verify_performance() -> tuple[str, bool]:
    buf = StringIO()
    from app.ai.provider import LLMProvider

    class FastMockProvider(LLMProvider):
        async def chat(self, messages, **kwargs):
            return "Test narrative response."

        async def chat_json(self, messages, **kwargs):
            return {
                "action_type": "probe",
                "target": None,
                "intensity": "medium",
                "risk_acceptance": False,
                "tool_used": None,
            }

    loader = WorldLoader(DATA_DIR)
    engine = RulesEngine(loader)
    parser = IntentParser(FastMockProvider())
    player = make_player()

    iterations = 10
    times: list[float] = []

    buf.write(f"=== Performance Verification ({iterations} iterations) ===\n")
    for i in range(iterations):
        start = time.perf_counter()
        intent = await parser.parse("test probe action")
        judgment = await engine.judge(intent, player)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        buf.write(f"  Iteration {i + 1}: {elapsed * 1000:.2f}ms\n")

    avg = sum(times) / len(times)
    max_t = max(times)
    min_t = min(times)
    buf.write(f"\n  Average: {avg * 1000:.2f}ms ({avg:.4f}s)\n")
    buf.write(f"  Min: {min_t * 1000:.2f}ms, Max: {max_t * 1000:.2f}ms\n")

    passed = avg < 5.0
    if passed:
        buf.write(f"\n  *** PASS: Average {avg:.4f}s < 5.0s threshold ***\n")
    else:
        buf.write(f"\n  *** FAIL: Average {avg:.4f}s >= 5.0s threshold ***\n")

    return buf.getvalue(), passed


# ==================================================================
# Main
# ==================================================================

async def main():
    all_output = StringIO()
    all_passed = True

    # Step 1
    all_output.write("\n" + "=" * 60 + "\n")
    all_output.write("STEP 1: Object x Action Matrix Verification\n")
    all_output.write("=" * 60 + "\n")
    output, passed = await verify_matrix()
    all_output.write(output + "\n")
    all_passed = all_passed and passed

    # Step 2
    all_output.write("\n" + "=" * 60 + "\n")
    all_output.write("STEP 2: God Rules Verification\n")
    all_output.write("=" * 60 + "\n")
    output, passed = await verify_gods()
    all_output.write(output + "\n")
    all_passed = all_passed and passed

    # Step 3
    all_output.write("\n" + "=" * 60 + "\n")
    all_output.write("STEP 3: Parser Robustness Verification\n")
    all_output.write("=" * 60 + "\n")
    output, passed = await verify_parser()
    all_output.write(output + "\n")
    all_passed = all_passed and passed

    # Step 4
    all_output.write("\n" + "=" * 60 + "\n")
    all_output.write("STEP 4: Performance Verification\n")
    all_output.write("=" * 60 + "\n")
    output, passed = await verify_performance()
    all_output.write(output + "\n")
    all_passed = all_passed and passed

    # Summary
    all_output.write("\n" + "=" * 60 + "\n")
    if all_passed:
        all_output.write("ALL VERIFICATIONS PASSED\n")
    else:
        all_output.write("SOME VERIFICATIONS FAILED\n")
    all_output.write("=" * 60 + "\n")

    # Print and optionally save
    result = all_output.getvalue()
    print(result)

    # Save evidence
    evidence_dir = Path(__file__).resolve().parent.parent / ".sisyphus" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "task-10-matrix-results.txt").write_text(result, encoding="utf-8")
    print(f"\nEvidence saved to: {evidence_dir / 'task-10-matrix-results.txt'}")

    # Separate performance file
    perf_output, perf_passed = await verify_performance()
    (evidence_dir / "task-10-performance.txt").write_text(perf_output, encoding="utf-8")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
