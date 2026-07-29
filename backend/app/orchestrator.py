"""Interaction loop orchestrator — chains parse -> judge -> render -> update."""

from __future__ import annotations

import logging
from copy import deepcopy

from app.api.deps import IntentParser, NarrativeRenderer, StateRepository
from app.engine.rules_engine import RulesEngine
from app.models.action import JudgmentResult
from app.models.api import ActionRequest, ActionResponse
from app.models.player import PlayerState

logger = logging.getLogger(__name__)


class Orchestrator:
    """Chains the full interaction loop: parse -> judge -> render -> update_state."""

    def __init__(
        self,
        parser: IntentParser,
        engine: RulesEngine,
        renderer: NarrativeRenderer,
        state_repo: StateRepository,
    ) -> None:
        self._parser = parser
        self._engine = engine
        self._renderer = renderer
        self._state_repo = state_repo

    async def process_action(self, request: ActionRequest) -> ActionResponse:
        """Process a player action through the full pipeline."""
        # 1. Get current player state
        player = await self._state_repo.get_state(player_id=request.player_id)
        if player is None:
            player = await self._state_repo.reset_state(player_id=request.player_id)

        # 2. Parse intent
        intent = await self._parser.parse(request.player_input)

        # 3. Judge
        judgment = await self._engine.judge(intent, player)

        # 4. Apply state changes
        updated_player = self._apply_state_changes(player, judgment)
        await self._state_repo.update_state(request.player_id, updated_player)

        # 5. Render narrative
        context: dict[str, object] = {
            "scene": player.location,
            "atmosphere": judgment.narrative_context.atmosphere,
        }
        try:
            narrative = await self._renderer.render(judgment, intent, context)
        except Exception:
            logger.exception("Narrative rendering failed, using template fallback")
            narrative = _template_render(judgment)

        # 6. Build response
        return ActionResponse(
            judgment=judgment,
            narrative=narrative,
            updated_state=updated_player,
            parsed_intent=intent,
            echo_vision="[Echo vision triggered]" if judgment.echo_triggered else None,
        )

    def _apply_state_changes(
        self, player: PlayerState, judgment: JudgmentResult
    ) -> PlayerState:
        """Apply judgment state changes to player. Returns a new PlayerState copy."""
        updated = deepcopy(player)

        for change in judgment.state_changes:
            if change.target_type != "player" or change.target_id != player.id:
                continue
            value = change.new_value
            if change.property_name == "health":
                updated.health = max(0, min(updated.max_health, int(value)))
            elif change.property_name == "energy":
                updated.energy = max(0, min(updated.max_energy, int(value)))
            elif change.property_name == "strength":
                updated.strength = max(0, min(100, int(value)))
            elif change.property_name == "mental_stability":
                updated.mental_stability = max(0, min(100, int(value)))
            elif change.property_name == "status":
                from app.models.player import PlayerStatus

                updated.status = PlayerStatus(value)

        # Apply direct damage
        if judgment.damage > 0:
            updated.health = max(0, updated.health - judgment.damage)

        return updated


def _template_render(judgment: JudgmentResult) -> str:
    """Minimal fallback narrative when the LLM renderer fails."""
    outcome = judgment.result.value
    reason = judgment.reason
    god = judgment.god_intervention
    if god:
        return f"[{god} INTERVENTION] {reason} (Result: {outcome})"
    return f"[SYSTEM] {reason} (Result: {outcome})"
