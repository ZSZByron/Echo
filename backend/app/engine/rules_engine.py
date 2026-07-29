"""Deterministic rules engine - the heart of Echo's judgment system."""
from __future__ import annotations

from typing import Optional

from app.engine.god_intervention import apply_penalty, check_intervention
from app.engine.physics import calculate_energy_cost, check_strength_vs_hardness
from app.engine.world_loader import WorldLoader
from app.models.action import (
    JudgmentOutcome,
    JudgmentResult,
    NarrativeContext,
    ParsedIntent,
    StateChange,
)
from app.models.player import PlayerState
from app.models.world import GameObject, GodKing, Scene


class RulesEngine:
    """100% deterministic. Same input -> same output. Zero AI calls."""

    def __init__(self, loader: WorldLoader) -> None:
        self._loader = loader
        self._gods = loader.load_gods()
        self._intervention_table = loader.load_intervention_table()

    async def judge(
        self, intent: ParsedIntent, player: PlayerState
    ) -> JudgmentResult:
        # === Section 1: Load scene and find target ===
        scene = self._loader.load_scene(player.location)
        target = self._find_target(scene, intent.target)

        # === Section 2: God intervention check (future anchors) ===
        god = check_intervention(
            intent.target or "", self._intervention_table, self._gods
        )
        if god is not None and target is not None and target.is_future_anchor:
            changes = apply_penalty(god, player.id)
            return self._build_result(
                JudgmentOutcome.FORCED_FAIL,
                intent, scene, target,
                reason=f"神王{god.name}干涉：{god.domain}领域的未来支点不可更改",
                god_intervention=god.name,
                state_changes=changes,
            )

        # === Section 3: Physics check ===
        if target is not None:
            success = check_strength_vs_hardness(
                player.strength, target.hardness
            )
            if success:
                return self._build_result(
                    JudgmentOutcome.SUCCESS,
                    intent, scene, target,
                    reason=f"力量校验通过 ({player.strength} >= {target.hardness})",
                )
            return self._build_result(
                JudgmentOutcome.FAIL,
                intent, scene, target,
                reason=f"力量不足 ({player.strength} < {target.hardness})",
            )

        # === Section 4: No target ===
        return self._build_result(
            JudgmentOutcome.SUCCESS,
            intent, scene, None,
            reason="无特定目标，动作执行",
        )

    def _find_target(
        self, scene: Scene, target_id: Optional[str]
    ) -> Optional[GameObject]:
        if target_id is None:
            return None
        for obj in scene.accessible_objects:
            if obj.id == target_id:
                return obj
        return None

    def _build_result(
        self,
        outcome: JudgmentOutcome,
        intent: ParsedIntent,
        scene: Scene,
        target: Optional[GameObject],
        reason: str,
        god_intervention: Optional[str] = None,
        state_changes: Optional[list[StateChange]] = None,
    ) -> JudgmentResult:
        active_gods: list[str] = []
        if god_intervention:
            active_gods.append(god_intervention)

        narrative = NarrativeContext(
            scene_id=scene.scene_id,
            previous_action=intent.raw_input,
            active_gods=active_gods,
            atmosphere=scene.atmosphere,
            tension_level=80 if god_intervention else 50,
        )

        damage = 0
        if god_intervention and state_changes:
            for change in state_changes:
                if change.property_name == "health":
                    damage = change.new_value

        return JudgmentResult(
            result=outcome,
            reason=reason,
            damage=damage,
            state_changes=state_changes or [],
            god_intervention=god_intervention,
            narrative_context=narrative,
            echo_triggered=False,
        )
