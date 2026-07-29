"""God intervention logic - deterministic checks for protected objects."""
from __future__ import annotations

from app.models.action import StateChange
from app.models.world import GodKing


def check_intervention(
    target_id: str,
    intervention_table: dict[str, str],
    gods: list[GodKing],
) -> GodKing | None:
    """Check if target is protected by a god. Returns the god or None."""
    if not target_id:
        return None
    god_id = intervention_table.get(target_id)
    if god_id is None:
        return None
    for god in gods:
        if god.id == god_id:
            return god
    return None


def apply_penalty(god: GodKing, player_id: str = "player") -> list[StateChange]:
    """Generate state changes for a god's penalty."""
    health_damage = god.penalty
    stability_damage = god.penalty // 2
    return [
        StateChange(
            target_type="player",
            target_id=player_id,
            property_name="health",
            old_value=0,
            new_value=health_damage,
        ),
        StateChange(
            target_type="player",
            target_id=player_id,
            property_name="mental_stability",
            old_value=0,
            new_value=stability_damage,
        ),
    ]
